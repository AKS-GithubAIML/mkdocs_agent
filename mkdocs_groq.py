import streamlit as st
import os
import requests
import re
import groq
import tiktoken

st.set_page_config(layout="wide")

# Sidebar for API Key input
st.sidebar.title("Configuration")
groq_api_key = st.sidebar.text_input("Enter your Groq API Key", type="password")

def extract_code_comments(code_content):
    """Extracts code comments and docstrings from the given code."""
    comments = []
    docstrings = []
    in_multiline_string = False
    multiline_string_quote = None

    for line in code_content.splitlines():
        line = line.strip()

        if in_multiline_string:
            if line.endswith(multiline_string_quote):
                in_multiline_string = False
                docstrings.append(line)
            else:
                docstrings.append(line)
            continue

        if line.startswith('"""') or line.startswith("'''"):
            in_multiline_string = True
            multiline_string_quote = '"""' if line.startswith('"""') else "'''"
            if line.endswith(multiline_string_quote):
                in_multiline_string = False
            docstrings.append(line)
            continue

        if line.startswith('#'):
            comments.append(line[1:].strip())
        elif '"""' in line or "'''" in line:
            docstrings.append(line)

    return comments, docstrings

def chunk_and_summarize(code_content, model="llama3-70b-8192", max_tokens=15000):
    """Chunks code, generates standalone documentation for each chunk."""
    if not groq_api_key:
        return ["Error: Groq API Key is required."]
    
    client = groq.Client(api_key=groq_api_key)
    chunks = []
    chunk_docs = []
    code_lines = code_content.splitlines()
    current_chunk = ""
    chunk_size = max_tokens // 3

    for line in code_lines:
        if len(current_chunk) + len(line) + 1 > chunk_size:
            if current_chunk:
                chunks.append(current_chunk)
                try:
                    doc_response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": "Generate comprehensive documentation for the following code chunk. Make it a self-contained section that can be concatenated with others."},
                            {"role": "user", "content": current_chunk},
                        ],
                    )
                    chunk_docs.append(doc_response.choices[0].message.content.strip())
                except Exception as e:
                    chunk_docs.append(f"Documentation Error: {e}")
                current_chunk = line + "\n"
        else:
            current_chunk += line + "\n"

    if current_chunk:
        chunks.append(current_chunk)
        try:
            doc_response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Generate comprehensive documentation for the following code chunk. Make it a self-contained section that can be concatenated with others."},
                    {"role": "user", "content": current_chunk},
                ],
            )
            chunk_docs.append(doc_response.choices[0].message.content.strip())
        except Exception as e:
            chunk_docs.append(f"Documentation Error: {e}")

    return chunk_docs

def generate_enhanced_markdown(code_content, filename="enhanced_code_documentation.md", model="llama3-70b-8192"):
    """Generates enhanced markdown documentation using Groq API."""
    if not groq_api_key:
        return "**Error: Groq API Key is required.**"
    
    client = groq.Client(api_key=groq_api_key)
    markdown = "## Enhanced Code Documentation\n\n"

    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        token_count = len(encoding.encode(code_content))

        if token_count > 15000:
            chunk_documentation = chunk_and_summarize(code_content)
            markdown += "\n\n".join(chunk_documentation)
            markdown += "\n\n### Original Code (Chunks):\n"
            code_chunks = code_content.split("```python\n")
            for i in range(len(code_chunks)):
                if i != 0:
                    markdown += "```python\n" + code_chunks[i] + "\n```\n\n"
        else:
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a code documentation expert. Analyze the provided Python code and generate comprehensive and informative documentation."},
                    {"role": "user", "content": f"Analyze this code and generate documentation:\n\n{code_content}"},
                ],
            )
            llm_documentation = completion.choices[0].message.content.strip()
            markdown += f"{llm_documentation}\n\n"
            markdown += "### Original Code:\n```python\n" + code_content + "\n```"

    except Exception as e:
        markdown += f"**LLM Documentation Generation Failed:** {e}\n\n"

    return markdown

def main():
    st.title("Enhanced Code Documentation Generator (LLM)")
    input_type = st.radio("Input Type", ("File URL/Path", "Code Text"))

    if input_type == "File URL/Path":
        file_path_or_url = st.text_input("Enter the file URL or local file path:")
        if st.button("Generate from File/URL (Enhanced)"):
            if file_path_or_url:
                try:
                    if file_path_or_url.startswith("http://") or file_path_or_url.startswith("https://"):
                        response = requests.get(file_path_or_url)
                        response.raise_for_status()
                        code_content = response.text
                    else:
                        with open(file_path_or_url, "r") as f:
                            code_content = f.read()

                    markdown_content = generate_enhanced_markdown(code_content)
                    st.download_button("Download Enhanced Markdown", markdown_content, file_name="enhanced_code_documentation.md", mime="text/markdown")
                    st.markdown(markdown_content)
                except requests.exceptions.RequestException as e:
                    st.error(f"Error fetching the file from URL: {e}")
                except FileNotFoundError:
                    st.error(f"Error: File not found at path: {file_path_or_url}")
                except Exception as e:
                    st.error(f"An unexpected error occurred: {e}")
            else:
                st.warning("Please enter a file URL or path.")
    elif input_type == "Code Text":
        code_text = st.text_area("Enter your code here:")
        if st.button("Generate from Text (Enhanced)"):
            if code_text:
                markdown_content = generate_enhanced_markdown(code_text)
                st.download_button("Download Enhanced Markdown", markdown_content, file_name="enhanced_code_documentation.md", mime="text/markdown")
                st.markdown(markdown_content)
            else:
                st.warning("Please enter some code.")

if __name__ == "__main__":
    main()