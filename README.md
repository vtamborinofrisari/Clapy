# Clapy
Clapy is a vibe coded open-source minimal Python3 script to use Claude AI models via terminal (API key is required). The project has been built with the help of Claude AI.

## Usage
```shell
python3 clapy.py --help
```
<br>

You have to set the Anthropic API key as an env variable in your shell:
```shell
export ANTHROPIC_API_KEY="YOUR_API_KEY"
```
<br>

Considering the output will be markdown text, you can pipe the output to glow (a terminal markdown renderer) with:
```shell
python3 clapy.py "Your prompt" | glow
```
It'll be much nicer.

## NOTES
The script has been tested and is currently my CLI tool of choice to interact with Claude models.

<br>

Bug reports and contribution are always welcome.
