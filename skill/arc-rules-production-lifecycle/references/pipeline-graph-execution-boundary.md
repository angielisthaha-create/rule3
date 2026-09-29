# Graph Execution Boundary

ARC owns Rule semantics and promotion eligibility; `graph-operations` owns live Neo4j execution. ARC may prepare exact write packets and expected outcomes but must not embed alternate active database-execution instructions.
