import os
import json
import torch
import urllib.error
import urllib.request
from unaiverse.agent import Agent
from unaiverse.modules.networks import SiteRAG
from unaiverse.modules.utils import ModuleWrapper
from unaiverse.networking.node.node import Node
from unaiverse.streams.dataprops import StreamType

"""
Dependencies:
Use a specific version of "transformers", otherwise "sentence-transformers" will complain.

pip install transformers==4.49.0 sentence-transformers langchain chromadb beautifulsoup4 requests
pip install tiktoken blobfile langchain-community
pip install --no-cache-dir --force-reinstall sentencepiece
"""

# The language model is the Qwen3.8-27B server shared by the agents of this machine (vLLM, OpenAI-compatible API)
VLLM_BASE_URL = os.environ.get("VLLM_BASE_URL", "http://127.0.0.1:8000/v1").rstrip("/")
VLLM_MODEL = os.environ.get("VLLM_MODEL", "qwen3.8-27b")


class QwenSiteRAG(SiteRAG):
    """SiteRAG whose answers are written by the Qwen server instead of a model loaded here: crawling, embedder and
    retrieval are the library's, so only the embedder takes GPU memory (on PROC_DEVICE)."""

    def __init__(self,
                 site_url: str,
                 site_folder: str = os.path.join("rag", "downloaded_site"),
                 db_folder: str = os.path.join("rag", "chroma_db"),
                 max_tokens: int = 512,
                 *args, **kwargs):
        from langchain.vectorstores import Chroma
        from langchain.embeddings import SentenceTransformerEmbeddings

        self.site_url = site_url
        self.site_folder = site_folder
        self.db_folder = db_folder

        # The full device name: the library passes only its type, which puts the embedder on cuda:0 whatever is asked
        self.embedder = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2",
                                                      model_kwargs={"device": os.getenv("PROC_DEVICE", "cpu")})
        self.crawl_website()
        self.crawled_site_to_rag_knowledge_base()
        retriever = Chroma(persist_directory=db_folder, embedding_function=self.embedder).as_retriever(
            search_kwargs={"k": 3})

        class Net(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self._retriever = retriever

            def forward(self, msg: str) -> str:
                docs = self._retriever.get_relevant_documents(msg)
                context = "\n\n".join(doc.page_content for doc in docs)
                body = {"model": VLLM_MODEL, "max_tokens": max_tokens,
                        "temperature": 0.7, "top_p": 0.8, "top_k": 20,  # Qwen's sampling for non-thinking mode
                        "chat_template_kwargs": {"enable_thinking": False},
                        "messages": [{"role": "system",
                                      "content": f"Answer the question using only the following context, taken from "
                                                 f"{site_url}. If the context does not contain the answer, say so. "
                                                 f"Answer in the language of the question.\n\n{context}"},
                                     {"role": "user", "content": msg}]}
                req = urllib.request.Request(f"{VLLM_BASE_URL}/chat/completions", method="POST",
                                             data=json.dumps(body).encode("utf-8"),
                                             headers={"Content-Type": "application/json"})
                try:
                    with urllib.request.urlopen(req, timeout=120) as resp:
                        out = json.loads(resp.read())["choices"][0]["message"]["content"].strip()
                except (urllib.error.URLError, OSError, ValueError, KeyError, IndexError):
                    return "The language model is not reachable right now, please retry in a minute."

                # Append the source URL of the best match, as the library does
                best_doc, _ = self._retriever.vectorstore.similarity_search_with_score(msg, k=1)[0]
                source = best_doc.metadata['source']
                return (out + "<br/><br/>\nURLs:\n<a href='" + source +
                        "' onclick='window.open(this.href); return false;' style='color: blue;'>" + source + "</a>")

        ModuleWrapper.__init__(
            self,
            module=Net(),
            proc_inputs=[StreamType(data_type="text", pubsub=False, private_only=False)],
            proc_outputs=[StreamType(data_type="text", pubsub=False, private_only=False)],
            *args, **kwargs)


# Agent
agent = Agent(proc=QwenSiteRAG(site_url="https://collectionless.ai/"), proc_inputs=["text"], proc_outputs=["text"])

# Node hosting agent
node_agent = Node(agent, node_name="SiteRAG", hidden=True, clock_delta=1. / 30.)

# Running node
node_agent.run()
