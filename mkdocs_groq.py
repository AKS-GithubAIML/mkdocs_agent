import streamlit as st
import requests
import groq
import tiktoken
from langchain.document_loaders import TextLoader, UnstructuredFileLoader
from langchain.document_loaders.web_base import WebBaseLoader

st.set_page_config(layout="wide")

# Sidebar for API Key input
st.sidebar.title("Configuration")
groq_api_key = st.sidebar.text_input("Enter your Groq API Key", type="password")

def load_file(uploaded_file):
    """Loads content from an uploaded file."""
    if uploaded_file is not None:
        return uploaded_file.getvalue().decode("utf-8")
    return None

def convert_github_url(url):
    """Converts GitHub file URL to raw content URL if needed."""
    if "github.com" in url and "blob" in url:
        return url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
    return url

def load_url(url):
    """Loads content from a URL, handling GitHub files properly."""
    try:
        url = convert_github_url(url)
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        st.error(f"Error loading URL: {e}")
        return None

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
            markdown += "**Code too large for direct processing. Chunking required.**"
        else:
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a code documentation expert. Generate comprehensive documentation for this code."},
                    {"role": "user", "content": f"Analyze and document this code:\n\n{code_content}"},
                ],
            )
            markdown += completion.choices[0].message.content.strip() + "\n\n"
            markdown += "### Original Code:\n```python\n" + code_content + "\n```"
    except Exception as e:
        markdown += f"**Error generating documentation:** {e}\n\n"
    
    return markdown

def main():
    st.title("Enhanced Code Documentation Generator (LLM)")
    input_type = st.radio("Input Type", ("Upload File", "File URL", "Code Text"))
    
    if input_type == "Upload File":
        uploaded_file = st.file_uploader("Upload a Python file", type=["py"])
        if st.button("Generate from File (Enhanced)"):
            code_content = load_file(uploaded_file)
            if code_content:
                markdown_content = generate_enhanced_markdown(code_content)
                st.download_button("Download Enhanced Markdown", markdown_content, file_name="enhanced_code_documentation.md", mime="text/markdown")
                st.markdown(markdown_content)
            else:
                st.warning("Please upload a valid file.")

    elif input_type == "File URL":
        file_url = st.text_input("Enter the file URL:")
        if st.button("Generate from URL (Enhanced)"):
            if file_url:
                code_content = load_url(file_url)
                if code_content:
                    markdown_content = generate_enhanced_markdown(code_content)
                    st.download_button("Download Enhanced Markdown", markdown_content, file_name="enhanced_code_documentation.md", mime="text/markdown")
                    st.markdown(markdown_content)
                else:
                    st.error("Failed to load content from the URL.")
            else:
                st.warning("Please enter a valid URL.")
    
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
