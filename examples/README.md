# Examples

- [`tofufy.yaml`](./tofufy.yaml) — example config file you can pass with
  `tofufy convert ./repo --config tofufy.yaml`.

Try a dry run against any Terraform repo on your machine:

```bash
tofufy convert ./your-repo --dry-run
```

List all available conversion rules:

```bash
tofufy rules
tofufy rules --category breaking
```
