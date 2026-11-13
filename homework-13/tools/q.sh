# source tools/q.sh; then: q <name> <<EOF ... EOF  — runs Cypher via cypher-shell, saves output to results/<name>.csv (needs .env sourced)
q() { "/d/!Projects/study_osint/homework-13/_downloads/neo4j-community-2026.10.1/bin/cypher-shell.bat" -u neo4j -p "$NEO4J_PASSWORD" --format plain 2>&1 | grep -v "incubator" | tee "/d/!Projects/study_osint/homework-13/results/$1.csv"; }
