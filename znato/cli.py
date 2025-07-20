import sys
from rich.console import Console

from . import client
from . import find_onto_duplicates
from . import generate_ontology
from . import generate_swrl

def main():
    if len(sys.argv) < 2:
        Console().print("[bold red]No command specified[/bold red]")
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]

    if command == "client":
        client.main(args)
    elif command == "find-duplicates":
        find_onto_duplicates.main(args)
    elif command == "generate-ontology":
        generate_ontology.main(args)
    elif command == "generate-swrl":
        generate_swrl.main(args)
    else:
        Console().print(f"[bold red]Unknown command: {command}[/bold red]")
        sys.exit(1)

if __name__ == "__main__":
    main()
