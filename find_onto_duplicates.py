import argparse
from rdflib import Graph, RDF, RDFS, OWL
from rdflib.namespace import split_uri
from difflib import SequenceMatcher
from rich.console import Console
from rich.table import Table

def similar(a: str, b: str) -> float:
    """Return similarity ratio between two strings."""
    return SequenceMatcher(None, a, b).ratio()

def get_label_or_localname(g, node):
    """Get rdfs:label if exists, otherwise local part of URI."""
    for _, _, label in g.triples((node, RDFS.label, None)):
        return str(label)
    try:
        _, local = split_uri(node)
        return local
    except Exception:
        return str(node)

def find_equivalent_classes(ttl_file: str, similarity_threshold: float = 0.8):
    g = Graph()
    g.parse(ttl_file, format="turtle")

    classes = set()

    for s, _, _ in g.triples((None, RDF.type, OWL.Class)):
        classes.add(s)
    for s, _, _ in g.triples((None, RDF.type, RDFS.Class)):
        classes.add(s)
    for s, _, o in g.triples((None, RDFS.subClassOf, None)):
        classes.add(s)
        classes.add(o)

    classes = list(classes)
    equivalents = []

    for i in range(len(classes)):
        for j in range(i + 1, len(classes)):
            c1, c2 = classes[i], classes[j]

            if (c1, OWL.equivalentClass, c2) in g or (c2, OWL.equivalentClass, c1) in g:
                equivalents.append((c1, c2, "explicit owl:equivalentClass"))
                continue

            label1 = get_label_or_localname(g, c1).lower()
            label2 = get_label_or_localname(g, c2).lower()

            sim = similar(label1, label2)
            if sim >= similarity_threshold:
                equivalents.append((c1, c2, f"label similarity {sim:.2f}"))

    return equivalents

def print_equivalent_classes(equivalents):
    console = Console()
    table = Table(title="Equivalent RDF Classes", show_lines=True)

    table.add_column("Class 1", style="cyan", overflow="fold")
    table.add_column("Class 2", style="cyan", overflow="fold")
    table.add_column("Reason", style="green", overflow="fold")

    for c1, c2, reason in equivalents:
        table.add_row(str(c1), str(c2), reason)

    console.print(table)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Detect equivalent RDF classes in a TTL ontology.")
    parser.add_argument("ttl_file", help="Path to the TTL ontology file.")
    parser.add_argument("--similarity", "-s", type=float, default=0.8,
                        help="Sim. threshold for label similarity (default: 0.8).")
    args = parser.parse_args()

    eq_classes = find_equivalent_classes(args.ttl_file, args.similarity)
    if eq_classes:
        print_equivalent_classes(eq_classes)
    else:
        Console().print("[bold yellow]No equivalent classes detected.[/bold yellow]")
