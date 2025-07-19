import os
import argparse
from dotenv import load_dotenv
from rdflib import Graph
from openai import OpenAI
from docx import Document

# Load environment variables from .env file
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Brakuje klucza OPENAI_API_KEY w pliku .env")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

def load_ontology_classes(ttl_path):
    g = Graph()
    g.parse(ttl_path, format="ttl")
    classes = set()
    for s, p, o in g.triples((None, None, None)):
        if str(p).endswith("type") and str(o).endswith("Class"):
            classes.add(str(s).split('#')[-1])
    return classes

def generate_swrl_rules(description, ontology_classes):
    prompt = f"""
Given the following ontology classes: {', '.join(ontology_classes)}

And the system description text:
\"\"\"
{description}
\"\"\"

Extract semantic rules from the description and express them as SWRL rules,
mapping terms in the description to ontology classes/properties as best as possible.

Return only SWRL rules in the following format:
1. Condition1(?x) ∧ Condition2(?x) → Conclusion(?x)
2. ...
Each rule must be numbered on a separate line using Arabic numerals (1., 2., ...).
Do not include any explanations, just the rules.
"""
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a precise semantic web expert."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )
    return response.choices[0].message.content.strip()


def read_docx(file_path):
    doc = Document(file_path)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)

def save_swrl_rules_numbered(rules_text, output_path):
    lines = [line.strip() for line in rules_text.splitlines() if line.strip()]
    with open(output_path, "w", encoding="utf-8") as f:
        for i, line in enumerate(lines, 1):
            f.write(f"{line}\n")

def main():
    parser = argparse.ArgumentParser(description="Extract SWRL rules from system description and ontology")
    parser.add_argument("-o", "--ontology", required=True, help="Path to ontology TTL file")
    parser.add_argument("-d", "--description", required=True, help="Path to system description DOCX file")
    args = parser.parse_args()

    ontology_classes = load_ontology_classes(args.ontology)
    description = read_docx(args.description)
    swrl_rules = generate_swrl_rules(description, ontology_classes)

    output_file = "generated_rules.swrl"
    save_swrl_rules_numbered(swrl_rules, output_file)

    print(f"SWRL rules saved to {output_file}")
    print("\nGenerated SWRL rules:\n")
    print(swrl_rules)

if __name__ == "__main__":
    main()
