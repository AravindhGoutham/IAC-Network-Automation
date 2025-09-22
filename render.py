#!/usr/bin/env python3

import yaml
import jinja2
import argparse
import os
import sys

def load_yaml(file_path):
    """Load YAML file and return as a dictionary."""
    try:
        with open(file_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error reading YAML file {file_path}: {e}")
        sys.exit(1)

def load_template(template_path):
    """Load Jinja2 template from file."""
    try:
        template_dir = os.path.dirname(template_path)
        template_file = os.path.basename(template_path)
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(searchpath=template_dir),
            trim_blocks=True,
            lstrip_blocks=True
        )
        return env.get_template(template_file)
    except Exception as e:
        print(f"Error loading Jinja2 template {template_path}: {e}")
        sys.exit(1)

def render_config(yaml_data, template):
    """Render configuration using template and YAML data."""
    try:
        return template.render(yaml_data)
    except Exception as e:
        print(f"Error rendering template: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Render network configs from YAML and Jinja2 template")
    parser.add_argument("--yaml", required=True, help="Path to the YAML file")
    parser.add_argument("--template", required=True, help="Path to the Jinja2 template file")
    parser.add_argument("--output", required=False, help="Optional output file")
    args = parser.parse_args()

    yaml_data = load_yaml(args.yaml)
    template = load_template(args.template)
    config = render_config(yaml_data, template)

    if args.output:
        try:
            with open(args.output, 'w') as f:
                f.write(config)
            print(f"Configuration rendered to {args.output}")
        except Exception as e:
            print(f"Error writing output file: {e}")
            sys.exit(1)
    else:
        print(config)

if __name__ == "__main__":
    main()
