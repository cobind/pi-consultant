import requests
import html2text
import json
import re
from urllib.request import urlopen
from urllib.error import URLError
from pocketlawyer.ingest import add_document


def get_markdown_from_url(url):
    try:
        # 1. Fetch the HTML content from the link
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an error for bad status codes (404, 500, etc.)

        # 2. Configure the HTML to Markdown converter
        converter = html2text.HTML2Text()
        converter.ignore_links = False      # Keep hyperlinks
        converter.ignore_images = True      # Keep image tags
        converter.ignore_emphasis = True    # Keep bold/italic formatting
        converter.body_width = 0            # Wrap text at 0 characters (no automatic line breaks)

        # 3. Convert and return the Markdown
        markdown_text = converter.handle(response.text)
        return markdown_text

    except requests.exceptions.RequestException as e:
        return f"Error fetching the URL: {e}"

baseUrl = "https://www.southeastern.edu/resources/policies/a_z_index/"
policyDict = {}


missingLetters = ['q', 'x', 'y', 'z']
for i in range(ord('a'), ord('z') + 1):
    curChar = chr(i)
    if curChar in missingLetters:
        continue

    print("Getting policy links starting with \'" + curChar + "\'...")
    letterUrl = "".join([baseUrl, curChar, "/"])
    letterUrlMarkdown = get_markdown_from_url(letterUrl)
    linksSectionStart = letterUrlMarkdown.find("###  ")
    linksSectionEnd = letterUrlMarkdown.find("* [Request Info]")

    linksString = letterUrlMarkdown[linksSectionStart+6:linksSectionEnd]

    links = linksString.split("\n\n")

    for j in range(0, len(links)):
        linkLine = links[j]
        if not j:
            continue

        title = linkLine[linkLine.find("[")+1:linkLine.find("]")]
        url = linkLine[linkLine.find("]")+2:]
        policyDict[title] = url

policyCount = len(policyDict)
print(str(policyCount) + " policy links found")

policyObjectList = []
addSuccesses = 0
for title, url in policyDict.items():
    if title.isspace():
        continue

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # Read and decode the byte response to a string
        html_content = response.text

        policyPdfMatch = re.search("/wp-content/uploads/policies/.+\.pdf", html_content)

        if policyPdfMatch:
            policyPdfRoute = "https://www.southeastern.edu" + policyPdfMatch.group().rstrip(")")
        else:
            print(title + " is not a PDF policy lol")
            continue


        policyObjectList.append(
            {
                "title": title,
                "source": url,
                "pdf" : policyPdfRoute
            }
        )

        print(title + " added to JSON")
        addSuccesses = addSuccesses + 1


    except URLError as e:
        print(f"Failed to reach the server: {e}")
        break

with open("sluPolicyData.json", "w", encoding="utf-8") as file:
    json.dump(policyObjectList, file, indent=4)
