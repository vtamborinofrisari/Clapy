# Clapy
Clapy is a vibe coded open-source Python3 script with minimal depencies to use Claude AI model via terminal (API key is required). The project has been built with with the help of Claude models.

## Usage
python3 clapy.py --help

Yoou have to set the Anthropic API key as an env variable in your shell:
export ANTHROPIC_API_KEY="YOUR_API_KEY"

Considering the output will be markdown text, you can pipe the output to glow (a terminal markdown renderer) with:
python3 clapy.py "Your prompt" | glow
It'll be much nicer.

## NOTES
The script has been tested and is currently my CLI tool of choice to interact with Claude models.
Bug reports and contribution are always welcome.
