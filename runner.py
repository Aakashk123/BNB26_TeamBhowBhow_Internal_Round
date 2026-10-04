from pathlib import Path

from app.adversarial.scenarios import catalog, run


def main():
    results = [run(s["id"]) for s in catalog()]
    path = Path(__file__).resolve().parents[3] / "reports/adversarial.md"
    path.parent.mkdir(exist_ok=True)
    rows = [
        "# Adversarial results",
        "",
        "Evidence snapshots use SIMULATED providers and real cryptography. Tests run the production policy engine.",
        "",
        "| Scenario | Result | Actual status |",
        "|---|---|---|",
    ]
    rows += [f"| {r['id']} | {'PASS' if r['passed'] else 'FAIL'} | {r['actual']['status']} |" for r in results]
    path.write_text("\n".join(rows) + "\n")
    print(f"{sum(r['passed'] for r in results)}/{len(results)} scenarios passed")
    return 0 if all(r["passed"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
