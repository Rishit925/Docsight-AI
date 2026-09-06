import { useEffect, useRef, useState } from "react";
import {
  checkHealth,
  getDocuments,
  uploadDocument,
  askQuestion as askQuestionApi,
  getConversation,
} from "./api/docsightApi";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import {
  Activity,
  Bot,
  ChevronDown,
  FileText,
  Image as ImageIcon,
  Loader2,
  MessageSquare,
  RefreshCw,
  Send,
  Sparkles,
  Table2,
  Trash2,
  Upload,
  X,
  XCircle,
  Plus,
} from "lucide-react";
import "./App.css";



function App() {
  // ==================================================
  // API / SYSTEM STATE
  // ==================================================

  const [apiOnline, setApiOnline] = useState(false);
  const [checkingApi, setCheckingApi] = useState(false);

  // ==================================================
  // DOCUMENT STATE
  // ==================================================

  const [selectedFile, setSelectedFile] = useState(null);
  const [document, setDocument] = useState(null);

  const [documentHistory, setDocumentHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const [processing, setProcessing] = useState(false);

  // ==================================================
  // CHAT STATE
  // ==================================================

  const [conversation, setConversation] = useState([]);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);

  // ==================================================
  // UI STATE
  // ==================================================

  const [error, setError] = useState("");
  const [showDocuments, setShowDocuments] = useState(true);

  const conversationEndRef = useRef(null);
  const fileInputRef = useRef(null);



  // ==================================================
  // INITIAL LOAD
  // ==================================================

  useEffect(() => {
    checkApi();
    loadDocumentHistory();
  }, []);



  // ==================================================
  // AUTO-SCROLL CHAT
  // ==================================================

  useEffect(() => {
    if (conversation.length === 0) {
      return;
    }

    conversationEndRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "end",
    });
  }, [conversation, asking]);



  // ==================================================
  // CHECK API
  // ==================================================

  const checkApi = async () => {
    setCheckingApi(true);

    try {
      const response = await checkHealth();

      if (response) {
        setApiOnline(true);
        setError("");
      } else {
        setApiOnline(false);
      }
    } catch (err) {
      console.error("API health check failed:", err);
      setApiOnline(false);
    } finally {
      setCheckingApi(false);
    }
  };



  // ==================================================
  // LOAD DOCUMENT HISTORY
  // ==================================================

  const loadDocumentHistory = async () => {
    setLoadingHistory(true);

    try {
      const response = await getDocuments();

      if (Array.isArray(response)) {
        setDocumentHistory(response);
      } else {
        setDocumentHistory([]);
      }
    } catch (err) {
      console.error(
        "Failed to load document history:",
        err
      );
    } finally {
      setLoadingHistory(false);
    }
  };



  // ==================================================
  // OPEN FILE PICKER
  // ==================================================

  const openFilePicker = () => {
    fileInputRef.current?.click();
  };



  // ==================================================
  // SELECT NEW FILE
  // ==================================================

  const handleFileChange = (event) => {
    const file = event.target.files?.[0];

    if (!file) {
      return;
    }

    if (
      file.type !== "application/pdf" &&
      !file.name.toLowerCase().endsWith(".pdf")
    ) {
      setError("Please select a PDF file.");
      event.target.value = "";
      return;
    }

    setSelectedFile(file);
    setDocument(null);
    setConversation([]);
    setQuestion("");
    setError("");
  };



  // ==================================================
  // REMOVE SELECTED FILE
  // ==================================================

  const removeSelectedFile = () => {
    setSelectedFile(null);
    setError("");

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };



  // ==================================================
  // PROCESS DOCUMENT
  // ==================================================

  const processDocument = async () => {
    if (!selectedFile) {
      setError("Please select a PDF document first.");
      return;
    }

    setProcessing(true);
    setError("");

    try {
      const response = await uploadDocument(
        selectedFile
      );

      setDocument(response);
      setConversation([]);
      setQuestion("");
      setSelectedFile(null);

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }

      await loadDocumentHistory();

    } catch (err) {
      console.error(
        "Document processing failed:",
        err
      );

      const message =
        err.response?.data?.detail ||
        "Failed to process the document. Please check that the backend is running.";

      setError(message);
    } finally {
      setProcessing(false);
    }
  };



  // ==================================================
  // LOAD CONVERSATION FOR DOCUMENT
  // ==================================================

  const loadConversation = async (documentId) => {
    if (!documentId) {
      return;
    }

    try {
      const response =
        await getConversation(documentId);

      const history =
        response?.conversations;

      if (!Array.isArray(history)) {
        setConversation([]);
        return;
      }

      const formattedConversation =
        history.map((item, index) => ({
          id:
            item.id ||
            `${documentId}-${index}`,

          question:
            item.question || "",

          answer:
            item.answer || "",

          route:
            item.route || "",

          contentTypes:
            item.content_types || [],

          sources:
            item.sources || [],

          comparison:
            item.comparison || null,
        }));

      setConversation(
        formattedConversation
      );

    } catch (err) {
      console.error(
        "Failed to load conversation:",
        err
      );

      setConversation([]);
    }
  };



  // ==================================================
  // OPEN DOCUMENT FROM HISTORY
  // ==================================================

  const openHistoricalDocument = async (
    historicalDocument
  ) => {
    if (!historicalDocument?.document_id) {
      return;
    }

    const selectedDocument = {
      document_id:
        historicalDocument.document_id,

      file_name:
        historicalDocument.file_name,

      total_pages:
        historicalDocument.total_pages,

      total_chunks:
        historicalDocument.total_chunks,

      text_chunks:
        historicalDocument.text_chunks,

      table_chunks:
        historicalDocument.table_chunks,

      image_chunks:
        historicalDocument.image_chunks,

      upload_time:
        historicalDocument.upload_time,
    };

    setDocument(selectedDocument);
    setSelectedFile(null);
    setQuestion("");
    setError("");

    await loadConversation(
      historicalDocument.document_id
    );
  };



  // ==================================================
  // START NEW CHAT
  // ==================================================

  const startNewChat = () => {
    setConversation([]);
    setQuestion("");
    setError("");
  };



  // ==================================================
  // ASK QUESTION
  // ==================================================

  const askQuestion = async (
    questionToAsk = question
  ) => {
    const cleanQuestion =
      questionToAsk.trim();

    if (!cleanQuestion) {
      return;
    }

    if (!document?.document_id) {
      setError(
        "Upload a document first so Docsight AI has something to understand."
      );
      return;
    }

    if (asking) {
      return;
    }

    setAsking(true);
    setError("");

    try {
      const result =
        await askQuestionApi({
          question: cleanQuestion,
          documentId:
            document.document_id,
          topK: 5,
        });

      setConversation(
        (previous) => [
          ...previous,
          {
            id:
              `${Date.now()}-${previous.length}`,

            question:
              cleanQuestion,

            answer:
              result?.answer ||
              "No answer was returned.",

            route:
              result?.route || "",

            contentTypes:
              result?.content_types || [],

            sources:
              result?.sources || [],

            comparison:
              result?.comparison || null,
          },
        ]
      );

      setQuestion("");

    } catch (err) {
      console.error(
        "Question request failed:",
        err
      );

      const message =
        err.response?.data?.detail ||
        "Failed to generate an answer. Please try again.";

      setError(message);

    } finally {
      setAsking(false);
    }
  };



  // ==================================================
  // QUESTION INPUT
  // ==================================================

  const handleQuestionKeyDown = (
    event
  ) => {
    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {
      event.preventDefault();

      if (
        !asking &&
        question.trim()
      ) {
        askQuestion();
      }
    }
  };



  // ==================================================
  // CLEAR CONVERSATION
  // ==================================================

  const clearConversation = () => {
    setConversation([]);
    setError("");
  };



  // ==================================================
  // FORMAT DATE
  // ==================================================

  const formatUploadTime = (value) => {
    if (!value) {
      return "";
    }

    try {
      const date = new Date(value);

      if (
        Number.isNaN(
          date.getTime()
        )
      ) {
        return "";
      }

      return date.toLocaleDateString(
        undefined,
        {
          day: "numeric",
          month: "short",
          year: "numeric",
        }
      );

    } catch (err) {
      return "";
    }
  };



  // ==================================================
  // DISPLAY DOCUMENT NAME
  // ==================================================

  const getDocumentName = (
    value
  ) => {
    if (!value) {
      return "Untitled document";
    }

    return value;
  };



  return (
    <div className="app-shell">

      {/* ==================================================
          SIDEBAR
          ================================================== */}

      <aside className="sidebar">

        {/* BRAND */}

        <div className="brand">

          <div className="brand-icon">
            <FileText size={24} />
          </div>

          <div>
            <h1>Docsight AI</h1>
            <p>
              Multimodal Intelligence
            </p>
          </div>

        </div>



        {/* NEW CHAT */}

        <button
          className="new-chat-button"
          onClick={startNewChat}
          disabled={
            asking ||
            processing
          }
        >
          <Plus size={18} />
          <span>New Chat</span>
        </button>



        <div className="sidebar-divider" />



        {/* API STATUS */}

        <section className="sidebar-section">

          <div className="section-heading">
            <Activity size={17} />
            <span>
              System Status
            </span>
          </div>

          <div
            className={`status-card ${
              apiOnline
                ? "status-online"
                : "status-offline"
            }`}
          >
            <span className="status-dot" />

            <span>
              {checkingApi
                ? "Checking API..."
                : apiOnline
                ? "API Online"
                : "API Offline"}
            </span>
          </div>

          <button
            className="secondary-button"
            onClick={checkApi}
            disabled={
              checkingApi
            }
          >
            <RefreshCw
              size={16}
              className={
                checkingApi
                  ? "spin"
                  : ""
              }
            />

            {checkingApi
              ? "Checking..."
              : "Check API"}
          </button>

        </section>



        <div className="sidebar-divider" />



        {/* DOCUMENTS */}

        <section className="sidebar-section history-section">

          <div className="section-heading">

            <div className="section-heading-main">
              <FileText size={17} />

              <span>
                Documents
              </span>
            </div>

            <button
              className="history-refresh-button"
              onClick={
                loadDocumentHistory
              }
              disabled={
                loadingHistory ||
                processing
              }
              title="Refresh documents"
              aria-label="Refresh documents"
            >
              <RefreshCw
                size={14}
                className={
                  loadingHistory
                    ? "spin"
                    : ""
                }
              />
            </button>

          </div>



          <button
            className="sidebar-upload-button"
            onClick={
              openFilePicker
            }
            disabled={
              processing
            }
          >
            <Upload size={16} />
            Add PDF
          </button>



          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
            onChange={
              handleFileChange
            }
            className="hidden-file-input"
          />



          {selectedFile && (
            <div className="selected-file">

              <div className="selected-file-info">

                <FileText size={17} />

                <div>

                  <strong
                    title={
                      selectedFile.name
                    }
                  >
                    {
                      selectedFile.name
                    }
                  </strong>

                  <span>
                    Ready to process
                  </span>

                </div>

              </div>



              <button
                className="icon-button"
                onClick={
                  removeSelectedFile
                }
                title="Remove file"
                aria-label="Remove selected file"
                disabled={
                  processing
                }
              >
                <XCircle size={17} />
              </button>

            </div>
          )}



          {selectedFile && (
            <button
              className="primary-button"
              onClick={
                processDocument
              }
              disabled={
                processing
              }
            >
              {processing ? (
                <>
                  <Loader2
                    size={17}
                    className="spin"
                  />
                  Processing...
                </>
              ) : (
                <>
                  <Sparkles size={17} />
                  Process PDF
                </>
              )}
            </button>
          )}



          <button
            className="documents-toggle"
            onClick={() =>
              setShowDocuments(
                (value) => !value
              )
            }
          >
            <span>
              {showDocuments
                ? "Hide documents"
                : "Show documents"}
            </span>

            <ChevronDown
              size={15}
              className={
                showDocuments
                  ? "documents-chevron-open"
                  : ""
              }
            />
          </button>



          {showDocuments && (
            <div className="history-list">

              {loadingHistory ? (
                <div className="history-loading">
                  <Loader2
                    size={15}
                    className="spin"
                  />

                  <span>
                    Loading documents...
                  </span>
                </div>
              ) : documentHistory.length === 0 ? (
                <div className="history-empty">
                  <FileText size={18} />

                  <span>
                    No documents yet
                  </span>
                </div>
              ) : (
                documentHistory.map(
                  (
                    historicalDocument
                  ) => {

                    const isCurrent =
                      document?.document_id ===
                      historicalDocument.document_id;

                    return (
                      <button
                        key={
                          historicalDocument.document_id
                        }
                        className={`history-item ${
                          isCurrent
                            ? "history-item-active"
                            : ""
                        }`}
                        onClick={() =>
                          openHistoricalDocument(
                            historicalDocument
                          )
                        }
                        disabled={
                          processing
                        }
                      >

                        <div className="history-file-icon">
                          <FileText
                            size={16}
                          />
                        </div>


                        <div className="history-item-content">

                          <strong
                            title={
                              historicalDocument.file_name
                            }
                          >
                            {getDocumentName(
                              historicalDocument.file_name
                            )}
                          </strong>

                          <span>
                            {
                              historicalDocument.total_pages
                            }{" "}
                            pages
                            {formatUploadTime(
                              historicalDocument.upload_time
                            )
                              ? ` • ${formatUploadTime(
                                  historicalDocument.upload_time
                                )}`
                              : ""}
                          </span>

                        </div>

                      </button>
                    );
                  }
                )
              )}

            </div>
          )}

        </section>



        {/* CURRENT DOCUMENT INFORMATION */}

        {document && (
          <>
            <div className="sidebar-divider" />

            <section className="sidebar-section">

              <div className="section-heading">
                <FileText size={17} />

                <span>
                  Current Document
                </span>
              </div>


              <div className="current-document">

                <div className="document-icon">
                  <FileText size={20} />
                </div>


                <div className="document-details">

                  <strong
                    title={
                      document.file_name
                    }
                  >
                    {
                      document.file_name
                    }
                  </strong>

                  <span>
                    {
                      document.total_pages
                    }{" "}
                    pages
                  </span>

                </div>

              </div>

            </section>
          </>
        )}

      </aside>



      {/* ==================================================
          MAIN CHAT AREA
          ================================================== */}

      <main className="main-content">

        {/* TOP BAR */}

        <header className="topbar">

          <div className="topbar-document">

            {document ? (
              <>
                <FileText
                  size={18}
                />

                <div>

                  <strong
                    title={
                      document.file_name
                    }
                  >
                    {
                      document.file_name
                    }
                  </strong>

                  <span>
                    Document workspace
                  </span>

                </div>
              </>
            ) : (
              <>
                <Sparkles
                  size={18}
                />

                <div>

                  <strong>
                    Docsight AI
                  </strong>

                  <span>
                    Document intelligence workspace
                  </span>

                </div>
              </>
            )}

          </div>



          <div className="topbar-status">

            <span
              className={`mini-status ${
                apiOnline
                  ? "online"
                  : "offline"
              }`}
            />

            {apiOnline
              ? "Connected"
              : "Disconnected"}

          </div>

        </header>



        {/* CHAT CONTENT */}

        <div className="chat-container">

          {/* EMPTY STATE */}

          {conversation.length === 0 && (
            <section className="chat-empty-state">

              <div className="chat-empty-icon">
                <Sparkles size={30} />
              </div>


              <span className="eyebrow">
                MULTIMODAL DOCUMENT AI
              </span>


              <h2>
                Ask anything about
                your documents.
              </h2>


              <p>
                Upload a PDF and start
                a conversation. Docsight
                AI keeps the conversation
                in context while
                automatically finding
                relevant document
                evidence.
              </p>


              {!document && (
                <button
                  className="empty-upload-button"
                  onClick={
                    openFilePicker
                  }
                >
                  <Upload size={17} />
                  Add your first PDF
                </button>
              )}


              {document && (
                <div className="empty-document-ready">

                  <FileText size={17} />

                  <span>
                    {
                      document.file_name
                    }{" "}
                    is ready. Ask your
                    first question below.
                  </span>

                </div>
              )}

            </section>
          )}



          {/* CONVERSATION */}

          {conversation.length > 0 && (
            <section className="conversation-section">

              <div className="conversation-list">

                {conversation.map(
                  (item) => (
                    <ConversationCard
                      key={item.id}
                      item={item}
                    />
                  )
                )}


                {asking && (
                  <div className="typing-row">

                    <div className="message-avatar assistant-avatar">
                      <Bot size={18} />
                    </div>

                    <div className="typing-card">

                      <span>
                        Docsight AI
                      </span>

                      <div className="typing-indicator">

                        <span />
                        <span />
                        <span />

                      </div>

                    </div>

                  </div>
                )}


                <div
                  ref={
                    conversationEndRef
                  }
                  className="conversation-end"
                  aria-hidden="true"
                />

              </div>

            </section>
          )}



          {/* ERROR */}

          {error && (
            <div
              className="error-banner"
              role="alert"
            >

              <XCircle size={19} />

              <span>
                {error}
              </span>

              <button
                onClick={() =>
                  setError("")
                }
                aria-label="Dismiss error"
                title="Dismiss"
              >
                <X size={17} />
              </button>

            </div>
          )}

        </div>



        {/* CHAT INPUT */}

        <div className="chat-input-area">

          <div className="chat-input-wrapper">

            <MessageSquare
              size={20}
            />

            <input
              type="text"
              value={
                question
              }
              onChange={(event) =>
                setQuestion(
                  event.target.value
                )
              }
              onKeyDown={
                handleQuestionKeyDown
              }
              placeholder={
                document
                  ? "Ask anything about your documents..."
                  : "Upload a PDF to start chatting..."
              }
              disabled={
                asking ||
                !document
              }
              aria-label="Ask Docsight AI"
            />


            <button
              className="send-button"
              onClick={() =>
                askQuestion()
              }
              disabled={
                asking ||
                !question.trim() ||
                !document
              }
              aria-label="Send question"
              title="Send question"
            >

              {asking ? (
                <Loader2
                  size={19}
                  className="spin"
                />
              ) : (
                <Send size={19} />
              )}

            </button>

          </div>


          <div className="chat-input-hint">

            <span>
              Docsight AI can answer questions,
              analyze tables and images, and
              compare relevant documents.
            </span>

            {conversation.length > 0 && (
              <button
                className="clear-chat-button"
                onClick={
                  clearConversation
                }
                disabled={
                  asking
                }
              >
                <Trash2
                  size={14}
                />
                Clear chat
              </button>
            )}

          </div>

        </div>

      </main>

    </div>
  );
}



// ==================================================
// CONVERSATION CARD
// ==================================================

function ConversationCard({
  item,
}) {
  const sources =
    Array.isArray(item.sources)
      ? item.sources
      : [];

  const contentTypes =
    Array.isArray(
      item.contentTypes
    )
      ? item.contentTypes
      : [];

  const comparison =
    item.comparison;


  const openSource = (source) => {
    if (!source?.document_id) {
      return;
    }

    const documentId = encodeURIComponent(
      source.document_id
    );

    const pageNumber = Number(
      source.page_number
    );

    const pageSuffix =
      Number.isInteger(pageNumber) &&
      pageNumber > 0
        ? `#page=${pageNumber}`
        : "";

    const fileUrl =
      `/api/documents/${documentId}/file${pageSuffix}`;

    window.open(
      fileUrl,
      "_blank",
      "noopener,noreferrer"
    );
  };


  return (
    <article className="conversation-card">

      {/* USER MESSAGE */}

      <div className="chat-message user-chat-message">

        <div className="message-avatar user-avatar">
          YOU
        </div>


        <div className="message-content">

          <span className="message-label">
            YOU
          </span>

          <p className="user-question">
            {item.question}
          </p>

        </div>

      </div>



      {/* AI MESSAGE */}

      <div className="chat-message assistant-chat-message">

        <div className="message-avatar assistant-avatar">
          <Bot size={18} />
        </div>


        <div className="message-content answer-content">

          <div className="answer-header">

            <span className="message-label">
              DOCSIGHT AI
            </span>


            <div className="answer-badges">

              {item.route && (
                <span className="badge badge-route">
                  {item.route}
                </span>
              )}


              {contentTypes.map(
                (type) => (
                  <span
                    className="badge badge-content"
                    key={type}
                  >
                    {type}
                  </span>
                )
              )}

            </div>

          </div>



          {/* COMPARISON CONTEXT */}

          {comparison?.enabled &&
            comparison?.comparison_documents
              ?.length > 0 && (
              <div className="comparison-context">

                <div className="comparison-context-title">
                  <Sparkles
                    size={15}
                  />

                  <span>
                    Comparing documents
                  </span>
                </div>


                <div className="comparison-document-list">

                  {comparison.comparison_documents.map(
                    (doc) => (
                      <span
                        className="comparison-document"
                        key={
                          doc.document_id ||
                          doc.file_name
                        }
                      >
                        <FileText
                          size={13}
                        />

                        {
                          doc.file_name
                        }
                      </span>
                    )
                  )}

                </div>

              </div>
            )}



          {/* MARKDOWN ANSWER */}

          <div className="answer-text">

            <ReactMarkdown
              remarkPlugins={[
                remarkGfm,
              ]}
              rehypePlugins={[
                rehypeRaw,
              ]}
              components={{

                h1: ({
                  children,
                }) => (
                  <h1 className="answer-heading answer-heading-1">
                    {children}
                  </h1>
                ),


                h2: ({
                  children,
                }) => (
                  <h2 className="answer-heading answer-heading-2">
                    {children}
                  </h2>
                ),


                h3: ({
                  children,
                }) => (
                  <h3 className="answer-heading answer-heading-3">
                    {children}
                  </h3>
                ),


                p: ({
                  children,
                }) => (
                  <p className="answer-paragraph">
                    {children}
                  </p>
                ),


                ul: ({
                  children,
                }) => (
                  <ul className="answer-list answer-unordered-list">
                    {children}
                  </ul>
                ),


                ol: ({
                  children,
                }) => (
                  <ol className="answer-list answer-ordered-list">
                    {children}
                  </ol>
                ),


                li: ({
                  children,
                }) => (
                  <li className="answer-list-item">
                    {children}
                  </li>
                ),


                strong: ({
                  children,
                }) => (
                  <strong className="answer-bold">
                    {children}
                  </strong>
                ),


                em: ({
                  children,
                }) => (
                  <em className="answer-italic">
                    {children}
                  </em>
                ),


                blockquote: ({
                  children,
                }) => (
                  <blockquote className="answer-blockquote">
                    {children}
                  </blockquote>
                ),


                code: ({
                  className,
                  children,
                  ...props
                }) => {

                  const isInline =
                    !className &&
                    !String(
                      children
                    ).includes("\n");


                  if (isInline) {
                    return (
                      <code
                        className="answer-inline-code"
                        {...props}
                      >
                        {children}
                      </code>
                    );
                  }


                  return (
                    <pre className="answer-code-block">
                      <code>
                        {children}
                      </code>
                    </pre>
                  );
                },


                table: ({
                  children,
                }) => (
                  <div className="answer-table-wrapper">

                    <table className="answer-table">
                      {children}
                    </table>

                  </div>
                ),


                thead: ({
                  children,
                }) => (
                  <thead className="answer-table-head">
                    {children}
                  </thead>
                ),


                tbody: ({
                  children,
                }) => (
                  <tbody className="answer-table-body">
                    {children}
                  </tbody>
                ),


                tr: ({
                  children,
                }) => (
                  <tr className="answer-table-row">
                    {children}
                  </tr>
                ),


                th: ({
                  children,
                }) => (
                  <th className="answer-table-header">
                    {children}
                  </th>
                ),


                td: ({
                  children,
                }) => (
                  <td className="answer-table-cell">
                    {children}
                  </td>
                ),


                br: () => (
                  <br />
                ),

              }}
            >
              {item.answer ||
                "No answer was returned."}
            </ReactMarkdown>

          </div>



          {/* SOURCES */}

          {sources.length > 0 && (
            <details className="sources">

              <summary>

                <span>

                  <FileText
                    size={16}
                  />

                  Sources (
                  {sources.length}
                  )

                </span>


                <ChevronDown
                  size={15}
                  className="source-chevron"
                />

              </summary>


              <div className="sources-list">

                {sources.map(
                  (
                    source,
                    index
                  ) => (

                    <div
                      className={`source-item ${
                        source.document_id
                          ? "source-item-clickable"
                          : ""
                      }`}
                      key={`${source.source}-${source.page_number}-${index}`}
                      role={
                        source.document_id
                          ? "button"
                          : undefined
                      }
                      tabIndex={
                        source.document_id
                          ? 0
                          : -1
                      }
                      onClick={() =>
                        openSource(source)
                      }
                      onKeyDown={(event) => {
                        if (
                          source.document_id &&
                          (event.key === "Enter" ||
                            event.key === " ")
                        ) {
                          event.preventDefault();
                          openSource(source);
                        }
                      }}
                      title={
                        source.document_id
                          ? "Open source PDF"
                          : "Source PDF unavailable"
                      }
                    >

                      <div className="source-number">
                        {index + 1}
                      </div>


                      <div className="source-info">

                        <strong
                          title={
                            source.source
                          }
                        >
                          {
                            source.source ||
                            "Document source"
                          }
                        </strong>


                        <span>
                          Page{" "}
                          {
                            source.page_number ??
                            "—"
                          }
                        </span>

                      </div>


                      <span className="source-type">
                        {
                          source.content_type ||
                          "text"
                        }
                      </span>

                    </div>

                  )
                )}

              </div>

            </details>
          )}

        </div>

      </div>

    </article>
  );
}



export default App;