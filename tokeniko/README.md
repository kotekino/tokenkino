# Tokeniko Neuro-Symbolic Architecture

## Tokeniko's Compilation Flow

1. **NLP Parsing & Disambiguation (Symbolic Phase):** Tokeniko receives a natural language sentence, performs grammatical deconstruction (POS tagging, dependency parsing), and resolves contextual references (e.g., it understands that "you" refers to itself, i.e., "tokeniko").
2. **Vector Semantic Lookup:** It queries the database (MongoDB) to retrieve the encyclopedic definitions and the "pure" base tensors (2925 dimensions) for each word/entity, linking them to their respective *synsets* (e.g., WordNet).
3. **Logical Intermediary Generation (LLC):** It builds a dual-track data structure:
   * **LLC Flat:** A flat dictionary for fast $O(1)$ memory access.
   * **LLC Recursive:** A syntax tree (AST) that faithfully maps the grammatical relationships and logical dependencies between clauses using formal operators (AND, THAT, CONV).
4. **Fuzzy Fusion Engine (Sub-Symbolic Phase):** It uses linear algebra (via NumPy) to calculate the true "meaning" of the entire sentence. It applies scalar multipliers for adverbs (e.g., "very" = 1.5), uses vectorized fuzzy logic operators (Min, Max, negations, and Gödel implications) to handle complex conditions without exceeding the **[-1, 1]** range, and stabilizes the root entity with a soft normalization (`tanh`).
5. **Compilation into the `TKZip` Format:** It encapsulates the mathematical outcome into a strictly typed, fixed-size format. The logical roles of the sentence (subject, predicate, direct object) are transformed into final tensors of exactly **3237 dimensions** (300 logical markers + 2925 semantic space + 12 spacetime).

---

**In short:** Tokeniko takes the abstraction and ambiguity of human words, breaks them down using formal logic, and fuses them into a fixed-size mathematical matrix (the `zip`), ready to be saved in the database as a **permanent, queryable, and geometrically comparable memory**.