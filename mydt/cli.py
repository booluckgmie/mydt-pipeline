"""Command-line interface:  mydt template|add-year|synth|run"""
from __future__ import annotations
import argparse
from pathlib import Path
from .template import build_template, add_year
from .synthetic import make_submissions
from .consolidate import consolidate
from .report import all_reports


def main(argv=None):
    ap = argparse.ArgumentParser(prog="mydt")
    sp = ap.add_subparsers(dest="cmd", required=True)
    t = sp.add_parser("template"); t.add_argument("path"); t.add_argument("--years", type=int, nargs="+", required=True)
    a = sp.add_parser("add-year"); a.add_argument("path"); a.add_argument("year", type=int)
    s = sp.add_parser("synth"); s.add_argument("outdir"); s.add_argument("-n", type=int, default=10)
    r = sp.add_parser("run"); r.add_argument("indir"); r.add_argument("outdir")
    args = ap.parse_args(argv)
    if args.cmd == "template":
        print(build_template(args.path, args.years))
    elif args.cmd == "add-year":
        print(add_year(args.path, args.year))
    elif args.cmd == "synth":
        print(f"{len(make_submissions(args.outdir, args.n))} workbooks written")
    else:
        files = sorted(Path(args.indir).glob("*.xlsx"))
        res = consolidate(files, args.outdir)
        reps = all_reports(res, Path(args.outdir) / "reports")
        iss = res["issues"]
        print(f"{len(files)} files | {len(iss)} issues ({(iss.severity=='error').sum()} errors) | {len(reps)} reports -> {args.outdir}")


if __name__ == "__main__":
    main()
