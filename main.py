#!/usr/bin/env python3
"""
HAR AI Analyzer — CLI entry point.

Usage:
  python main.py light_0.json
  python main.py light_0.json light_1.json heavy_1.json
  python main.py --all
  python main.py --all --output report.json
"""

import argparse
import json
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from analyzer.loader import load_file, load_directory, load_files
from analyzer.context_builder import build_context
from analyzer.bedrock_client import BedrockClient
from analyzer.prompts import SYSTEM_PROMPT, single_file_prompt
from analyzer.reporter import print_single_report, save_report


def main():
    parser = argparse.ArgumentParser(description="Gen-AI HAR Analysis Tool")
    parser.add_argument("files", nargs="*", help="Analysis JSON files to process")
    parser.add_argument("--all", action="store_true", help="Analyze all JSON files in current directory")
    parser.add_argument("--output", metavar="FILE", help="Save results to a JSON file")
    parser.add_argument("--region", default=os.getenv("AWS_REGION", "ap-south-1"))
    parser.add_argument("--model", default=None)
    args = parser.parse_args()

    if args.all:
        loaded_files = load_directory(".")
        loaded_files = [f for f in loaded_files if not f["filename"].startswith("report")]
        if not loaded_files:
            print("No JSON files found in current directory.")
            sys.exit(1)
        print(f"\nFound {len(loaded_files)} files: {[f['filename'] for f in loaded_files]}")
    elif args.files:
        loaded_files = load_files(args.files)
    else:
        parser.print_help()
        sys.exit(1)

    client_kwargs = {"region": args.region}
    if args.model:
        client_kwargs["model_id"] = args.model
    client = BedrockClient(**client_kwargs)

    print("\n── Individual File Analysis ──────────────────────────────────")
    individual_results = []
    for loaded in loaded_files:
        print(f"  Analyzing {loaded['filename']}...")
        try:
            context = build_context(loaded)
            prompt = single_file_prompt(context)
            result = client.analyze(prompt, SYSTEM_PROMPT)
            individual_results.append(result)
            if result.get("parse_error"):
                print(f"\n[Parse error] Raw response:\n{result.get('raw_response')}")
            else:
                print_single_report(result)
        except Exception as e:
            print(f"  ERROR: {e}")

    if args.output:
        save_report({"individual": individual_results}, args.output)

    print("\nDone.\n")


if __name__ == "__main__":
    main()
