# Schema Figure Workflow

DBmiRNA keeps the editable schema figure source in DBML:

- [dbmirna.dbml](/homes/ezach01/DBmiRNA/docs/schema/dbmirna.dbml)

DBML is the text format used by dbdiagram.io. Treat this file as the source of truth for a dbdiagram-style database figure.

## Edit the Figure

1. Open [dbmirna.dbml](/homes/ezach01/DBmiRNA/docs/schema/dbmirna.dbml).
2. Add, remove, or rename tables, columns, indexes, and `ref` relationships.
3. Keep table names aligned with [sql/schema.sql](/homes/ezach01/DBmiRNA/sql/schema.sql).

Example relationship:

```dbml
gene_id text [not null, ref: > core.genes.id]
```

## Reproduce the Figure in dbdiagram.io

1. Go to `https://dbdiagram.io`.
2. Create a new diagram.
3. Paste the full contents of [dbmirna.dbml](/homes/ezach01/DBmiRNA/docs/schema/dbmirna.dbml).
4. Use dbdiagram.io's export menu to save the figure as PNG, SVG, or PDF.

## Recommended Export

Use SVG for documents and manuscripts because it stays sharp when resized. Use PNG only when a tool does not support SVG.

## Maintenance Rule

When the PostgreSQL schema changes, update both:

- [sql/schema.sql](/homes/ezach01/DBmiRNA/sql/schema.sql)
- [dbmirna.dbml](/homes/ezach01/DBmiRNA/docs/schema/dbmirna.dbml)

The SQL file is for the database. The DBML file is for the visual schema figure.
