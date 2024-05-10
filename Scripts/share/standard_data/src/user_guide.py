from pathlib import Path

import markdown

src_dir = Path(__file__).resolve().parent
out_dir = src_dir.parent.joinpath('output')
user_guide_file = out_dir.joinpath('data_user_guide.md')

template = """<!DOCTYPE html>
<html>
<head>
<title>CMAP Travel Demand Model Data User Guide</title>
<style>
html, body {
	font-family: var(--markdown-font-family, -apple-system, BlinkMacSystemFont, "Segoe WPC", "Segoe UI", system-ui, "Ubuntu", "Droid Sans", sans-serif);
	font-size: var(--markdown-font-size, 14px);
	padding: 0 26px;
	line-height: var(--markdown-line-height, 22px);
	word-wrap: break-word;
}

body {
	padding-top: 1em;
}

/* Reset margin top for elements */
h1, h2, h3, h4, h5, h6,
p, ol, ul, pre {
	margin-top: 0;
}

h1, h2, h3, h4, h5, h6 {
	font-weight: 600;
	margin-top: 24px;
	margin-bottom: 16px;
	line-height: 1.25;
}

/* Prevent `sub` and `sup` elements from affecting line height */
sub,
sup {
	line-height: 0;
}

ul ul:first-child,
ul ol:first-child,
ol ul:first-child,
ol ol:first-child {
	margin-bottom: 0;
}

p {
	margin-bottom: 16px;
}

li p {
	margin-bottom: 0.7em;
}

ul,
ol {
	margin-bottom: 0.7em;
}

h1 {
	font-size: 2em;
	margin-top: 0;
	padding-bottom: 0.3em;
	border-bottom-width: 1px;
	border-bottom-style: solid;
}

h2 {
	font-size: 1.5em;
	padding-bottom: 0.3em;
	border-bottom-width: 1px;
	border-bottom-style: solid;
}

h3 {
	font-size: 1.25em;
}

h4 {
	font-size: 1em;
}

h5 {
	font-size: 0.875em;
}

h6 {
	font-size: 0.85em;
}

table {
	border-collapse: collapse;
	margin-bottom: 0.7em;
}

th {
	text-align: left;
	border-bottom: 1px solid;
}

th,
td {
	padding: 5px 10px;
}

table > tbody > tr + tr > td {
	border-top: 1px solid;
}
</style>
</head>
<body>
{{content}}
</body>
</html>
"""
# Read Markdown from file.
with open(user_guide_file, encoding='utf-8') as user_guide:
    md = user_guide.read()
# Convert Markdown to HTML.
html = markdown.markdown(text=md, extensions=['tables'])
# Add HTML to template.
doc = template.replace('{{content}}', html)
# Write to file.
with open(user_guide_file.with_suffix('.html'), mode='w', encoding='utf-8') as user_guide:
    user_guide.write(doc)