ZnaTo is a Python module for analyzing and generating RDF ontologies and SWRL rules based on documents and TTL files.  

The project includes CLI tools to:

- Detect equivalent RDF classes in TTL ontologies  
- Generate RDF ontology from documents in a folder  
- Generate SWRL rules based on system description and ontology  
- Interact through a CLI client (ask questions using ontology and rules)  

---


## Installation



1. Clone the repository:

`git clone https://github.com/your\_username/znato.git`

`cd znato`



2. Create and activate a virtual environment (optional):

`python3 -m venv .venv`

`source .venv/bin/activate  # Linux/macOS`

`.venv\\\\Scripts\\\\activate   # Windows`



3. Install the module with dependencies:

`pip install .`



---



## Usage



The module is run via CLI. Command structure:

`python3 -m znato.cli <command> \[arguments]`



---



### Available commands and arguments



| Command           | Description                                                | Arguments                                                                                                  |
|-------------------|------------------------------------------------------------|------------------------------------------------------------------------------------------------------------|
| `client`          | Query interface for system (ontology + SWRL)               | -o, --ontology (TTL file path, required)<br>-s, --swrl (SWRL file path, required)<br>-q, --question (question text, required) |
| `find-duplicates` | Detect equivalent RDF classes in TTL file                  | ttl_file (TTL file path, required)<br>-s, --similarity (similarity threshold, default 0.8)                 |
| `generate-ontology` | Generate RDF ontology from documents in folder             | input (folder path with documents, required)<br>--output (output TTL file, default ontology.ttl)<br>--chunk_size (int, default 4000)<br>--overlap_size (int, default 500)<br>--delay_between_chunks (float, default 2.0) |
| `generate-swrl`   | Generate SWRL rules from system description and ontology   | -o, --ontology (TTL file path, required)<br>-d, --description (DOCX file path, required)                 |



---



## Usage Examples

Here are some examples of how to use the `znato.cli` commands:

---

### Detect Equivalent RDF Classes

To detect equivalent RDF classes within an ontology file, run:

`python3 -m znato.cli find-duplicates ontology.ttl -s 0.85`


---

### Generate RDF Ontology

To generate an RDF ontology from documents located in a folder, use:

`python3 -m znato.cli generate-ontology ./docs --output my_ontology.ttl --chunk_size 3000`


---

### Generate SWRL Rules

To generate SWRL rules based on an ontology and a system description, execute:

`python3 -m znato.cli generate-swrl -o ontology.ttl -d system_description.docx`


---

### Ask a Question Through the Client

To query the system with a question using an ontology and generated SWRL rules, use the client command:

`python3 -m znato.cli client -o ontology.ttl -s generated_rules.swrl -q "How to exchange points for a reward?"`





---



## License



The project is licensed under MIT License.

