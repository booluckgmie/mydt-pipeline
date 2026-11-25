"""Command-line interface:  mydt template|add-year|synth|run"""
from __future__ import annotations
import argparse
from pathlib import Path
from .template import build_template, add_year, prefill
from .i18n import LANGS
from .synthetic import make_submissions
from .consolidate import consolidate
from .report import all_reports


def main(argv=None):
    ap = argparse.ArgumentParser(prog="mydt")
    sp = ap.add_subparsers(dest="cmd", required=True)
    t = sp.add_parser("template"); t.add_argument("path"); t.add_argument("--years", type=int, nargs="+", required=True)
    t.add_argument("--lang", choices=LANGS, default="en", help="label language (structure is identical)")
    a = sp.add_parser("add-year"); a.add_argument("path"); a.add_argument("year", type=int)
    s = sp.add_parser("synth"); s.add_argument("outdir"); s.add_argument("-n", type=int, default=10)
    s.add_argument("--lang", choices=LANGS, default="en")
    f = sp.add_parser("prefill", help="write country metadata into a template (or a whole folder from a CSV)")
    f.add_argument("path"); f.add_argument("--country"); f.add_argument("--iso3")
    f.add_argument("--survey-year", type=int); f.add_argument("--contact-name"); f.add_argument("--contact-email")
    r = sp.add_parser("run"); r.add_argument("indir"); r.add_argument("outdir")
    args = ap.parse_args(argv)
    if args.cmd == "template":
        print(build_template(args.path, args.years, lang=args.lang))
    elif args.cmd == "add-year":
        print(add_year(args.path, args.year))
    elif args.cmd == "synth":
        print(f"{len(make_submissions(args.outdir, args.n, lang=args.lang))} workbooks written")
    elif args.cmd == "prefill":
        print(prefill(args.path, args.country, args.iso3, args.survey_year, args.contact_name, args.contact_email))
    else:
        files = sorted(Path(args.indir).glob("*.xlsx"))
        res = consolidate(files, args.outdir)
        reps = all_reports(res, Path(args.outdir) / "reports")
        iss = res["issues"]
        print(f"{len(files)} files | {len(iss)} issues ({(iss.severity=='error').sum()} errors) | {len(reps)} reports -> {args.outdir}")


if __name__ == "__main__":
    main()
