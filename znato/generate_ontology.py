import os
import json
import argparse
import pypandoc
import PyPDF2
from pathlib import Path
from slugify import slugify
from dotenv import load_dotenv
from docx import Document
from openai import OpenAI
from rdflib import Graph, Namespace, RDF, RDFS
from pydantic import BaseModel, ValidationError, Field
from typing import List
from rich.console import Console
from rich.panel import Panel
import time
import subprocess  # ✅ konwersja .doc -> .docx

# --- Konfiguracja środowiska ---
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Brakuje klucza OPENAI_API_KEY w pliku .env")

# ✅ wyłączenie spinnerów i kolorów w rich
console = Console(force_terminal=False, no_color=True)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

_pandoc_download_attempted = False
_pandoc_path = None

LLM_PROMPT_TEMPLATE = """
You are a knowledge engineer.

Extract a meta-graph (ontology-level knowledge) from the following text describing a system or domain.

Focus on abstract, general concepts (e.g. Entity, Process, Resource) and their semantic relationships (e.g. PARTICIPATES_IN, PRODUCES, DEPENDS_ON). Avoid overly specific or implementation-related terms.

Ensure:

    Each concept is abstract and unique.

    Each concept appears only once.

    Only semantic-level relationships are included.

    Do not include specific instances, data values, or example cases.

Respond in this strict JSON format:

{{ 
  "concepts": [
    {{ "id": "ConceptName1" }},
    {{ "id": "ConceptName2" }}
  ],
  "relationships": [
    {{
      "source": "ConceptName1",
      "target": "ConceptName2",
      "type": "RELATION_TYPE"
    }}
  ]
}}

Respond only with valid JSON object.
Text:
\"\"\"{text}\"\"\"
"""

class Concept(BaseModel):
    id: str

class Relationship(BaseModel):
    source: str
    target: str
    type: str = Field(..., alias="type")

class MetaGraph(BaseModel):
    concepts: List[Concept]
    relationships: List[Relationship]

# --- Wczytywanie plików ---

def convert_doc_to_docx(doc_path: Path) -> Path:
    output_dir = doc_path.parent
    try:
        subprocess.run([
            "soffice",
            "--headless",
            "--convert-to", "docx",
            "--outdir", str(output_dir),
            str(doc_path)
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_dir / (doc_path.stem + ".docx")
    except Exception as e:
        console.print(f"Błąd konwersji {doc_path.name}: {e}")
        return None

def load_docx(path: Path) -> str:
    try:
        doc = Document(path)
        return "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())
    except Exception as e:
        console.print(f"Ostrzeżenie: Nie udało się odczytać .docx {path.name}: {e}")
        return ""

def load_doc(path: Path) -> str:
    docx_path = convert_doc_to_docx(path)
    if docx_path and docx_path.exists():
        return load_docx(docx_path)
    else:
        return ""

def load_pdf(path: Path) -> str:
    text_content = []
    try:
        with open(path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_content.append(text.strip())
        return "\n".join(text_content)
    except Exception as e:
        console.print(f"Ostrzeżenie: Nie udało się odczytać .pdf {path.name}: {e}")
        return ""

def load_text(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8')
    except Exception as e:
        console.print(f"Ostrzeżenie: Nie udało się odczytać {path.name}: {e}")
        return ""

def process_folder(folder_path: str) -> str:
    base_path = Path(folder_path)
    if not base_path.is_dir():
        raise FileNotFoundError(f"Ścieżka '{folder_path}' nie jest folderem.")
    
    supported = {
        ".docx": load_docx,
        ".doc": load_doc,
        ".pdf": load_pdf,
        ".txt": load_text,
        ".md": load_text
    }

    all_files = [p for p in base_path.rglob("*") if p.is_file()]
    supported_files = [p for p in all_files if p.suffix.lower() in supported]

    all_texts = []
    for file_path in supported_files:
        console.print(f"Przetwarzanie: {file_path.name}")
        loader = supported.get(file_path.suffix.lower())
        if loader:
            content = loader(file_path)
            if content:
                all_texts.append(content)

    return "\n\n---\n\n".join(all_texts)

# --- Chunking i ekstrakcja ---

def chunk_text(text: str, chunk_size: int, overlap_size: int = 0) -> List[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap_size
    return chunks

def extract_meta_graph_from_chunk(text_chunk: str, delay: float = 0) -> MetaGraph:
    prompt = LLM_PROMPT_TEMPLATE.format(text=text_chunk)
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        parsed = json.loads(content)
        if delay > 0:
            time.sleep(delay)
        return MetaGraph(**parsed)
    except Exception as e:
        console.print(f"Błąd LLM: {e}")
        return MetaGraph(concepts=[], relationships=[])

def aggregate_meta_graphs(list_of_meta_graphs: List[MetaGraph]) -> MetaGraph:
    unique_concepts = {}
    unique_rels = {}

    for mg in list_of_meta_graphs:
        for c in mg.concepts:
            unique_concepts[slugify(c.id)] = c

        for r in mg.relationships:
            key = (slugify(r.source), slugify(r.target), slugify(r.type))
            if key not in unique_rels:
                unique_rels[key] = Relationship(source=r.source, target=r.target, type=r.type)

    final_concepts = list(unique_concepts.values())
    final_rels = list(unique_rels.values())

    return MetaGraph(concepts=final_concepts, relationships=final_rels)

def save_meta_graph_as_turtle(meta_data: MetaGraph, output_path: str, base_uri: str = "http://example.org/ontology#"):
    g = Graph()
    NS = Namespace(base_uri)

    for concept in meta_data.concepts:
        cid = slugify(concept.id, separator="_")
        g.add((NS[cid], RDF.type, RDFS.Class))

    for rel in meta_data.relationships:
        src = slugify(rel.source, separator="_")
        tgt = slugify(rel.target, separator="_")
        prop = slugify(rel.type, separator="_")

        g.add((NS[prop], RDF.type, RDF.Property))
        g.add((NS[prop], RDFS.domain, NS[src]))
        g.add((NS[prop], RDFS.range, NS[tgt]))

    g.serialize(destination=output_path, format="turtle")
    console.print(f"Ontologia zapisana jako {output_path}")

# --- Główna funkcja ---

def main(input_path: str, output_path: str, chunk_size: int, overlap_size: int, delay_between_chunks: float):
    console.print(f"📁 Przetwarzany folder: {input_path}")
    text = process_folder(input_path)

    if not text.strip():
        console.print("❌ Brak danych tekstowych do przetworzenia.")
        save_meta_graph_as_turtle(MetaGraph(concepts=[], relationships=[]), output_path)
        return

    chunks = chunk_text(text, chunk_size, overlap_size)
    console.print(f"🔎 Podzielono tekst na {len(chunks)} chunków.")

    all_graphs = []
    for i, chunk in enumerate(chunks):
        console.print(f"🧠 Chunk {i+1}/{len(chunks)}")
        graph = extract_meta_graph_from_chunk(chunk, delay=delay_between_chunks)
        all_graphs.append(graph)

    final_graph = aggregate_meta_graphs(all_graphs)
    console.print(f"✅ Finalna liczba pojęć: {len(final_graph.concepts)}, relacji: {len(final_graph.relationships)}")
    save_meta_graph_as_turtle(final_graph, output_path)

# --- CLI ---

import argparse
from .core import generate_ontology  # lub z odpowiedniego modułu

def main(args=None):
    parser = argparse.ArgumentParser(
        description="Generate RDF ontology from documents in a folder."
    )
    parser.add_argument("input", help="Path to folder with documents (.doc, .docx, .pdf, .txt, .md)")
    parser.add_argument("--output", default="ontology.ttl", help="Output TTL file")
    parser.add_argument("--chunk_size", type=int, default=4000, help="Chunk size (characters)")
    parser.add_argument("--overlap_size", type=int, default=500, help="Overlap between chunks (characters)")
    parser.add_argument("--delay_between_chunks", type=float, default=2.0, help="Delay between chunks (seconds)")

    parsed_args = parser.parse_args(args)

    try:
        generate_ontology(
            parsed_args.input,
            parsed_args.output,
            parsed_args.chunk_size,
            parsed_args.overlap_size,
            parsed_args.delay_between_chunks,
        )
        print("Ontology successfully generated.")
    except Exception as e:
        print(f"Critical error: {e}")

