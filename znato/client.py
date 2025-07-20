import os
import argparse
from dotenv import load_dotenv
from rdflib import Graph
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Brakuje klucza OPENAI_API_KEY w pliku .env")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

def load_ontology(ttl_path):
    g = Graph()
    g.parse(ttl_path, format="ttl")
    return g

def load_swrl_rules(swrl_path):
    with open(swrl_path, "r", encoding="utf-8") as f:
        return f.read()

def build_prompt(ontology_graph, swrl_rules, question):
    classes = set()
    properties = set()
    for s, p, o in ontology_graph.triples((None, None, None)):
        if str(p).endswith("type"):
            if str(o).endswith("Class"):
                classes.add(str(s).split("#")[-1])
            elif str(o).endswith("ObjectProperty") or str(o).endswith("DatatypeProperty"):
                properties.add(str(s).split("#")[-1])
    classes_list = ", ".join(sorted(classes))
    properties_list = ", ".join(sorted(properties))

    prompt = f"""
You are an expert in semantic web, OWL ontologies, and system modeling using SWRL rules.

Ontology classes:
{classes_list}

Ontology properties:
{properties_list}

SWRL rules:
{swrl_rules}

Using the ontology and SWRL rules above, answer the following question about the system's functionality:

Question:
{question}

Instructions for answering:
- Apply multi-step logical reasoning.
- For each reasoning step:
  - Identify the SWRL rule(s) used (by rule number).
  - Indicate which OWL classes and properties are involved in the rule.
  - Describe the condition(s) satisfied and the resulting conclusion.
- Proceed step-by-step, explaining the sequence of logical inferences.
- Use formal language, but ensure clarity.
- Provide a final conclusion summarizing what must be true or done in the system to fulfill the question's goal.

Structure the answer clearly with numbered reasoning steps and refer to OWL entities precisely.

"""
    return prompt.strip()

def ask_question(ontology_path, swrl_path, question):
    ontology_graph = load_ontology(ontology_path)
    swrl_rules = load_swrl_rules(swrl_path)
    prompt = build_prompt(ontology_graph, swrl_rules, question)

    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a precise semantic web expert."},
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        max_tokens=1024,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        seed=42 # Dodaj ten parametr z dowolną stałą liczbą całkowitą
    )
    return response.choices[0].message.content.strip()

def main(args=None):
    parser = argparse.ArgumentParser(
        description="Client interface for querying ontology using SWRL + LLM"
    )
    parser.add_argument("-o", "--ontology", required=True, help="Path to ontology TTL file")
    parser.add_argument("-s", "--swrl", required=True, help="Path to SWRL rules file")
    parser.add_argument("-q", "--question", required=True, help="Question to ask")

    parsed_args = parser.parse_args(args)  # <--- najważniejsza linia

    # Teraz możesz bezpiecznie używać parsed_args
    answer = ask_question(parsed_args.ontology, parsed_args.swrl, parsed_args.question)
    print(answer)
