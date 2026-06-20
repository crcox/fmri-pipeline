# src/glm_prep/cli.py

import argparse
from glm_prep.parser import load_policy
from glm_prep.execute import build_design_matrix


def main():
    parser = argparse.ArgumentParser(description="GLM Prep Worker")

    parser.add_argument("--policy", required=True)
    parser.add_argument("--bold", required=True)
    parser.add_argument("--events", required=True)
    parser.add_argument("--confounds", required=True)
    parser.add_argument("--tedana", required=False)
    parser.add_argument("--out-dir", required=True)

    args = parser.parse_args()

    policy = load_policy(args.policy)

    build_design_matrix(
        bold_path=args.bold,
        events_path=args.events,
        confounds_path=args.confounds,
        tedana_path=args.tedana,
        policy=policy,
        out_dir=args.out_dir,
    )


if __name__ == "__main__":
    main()
