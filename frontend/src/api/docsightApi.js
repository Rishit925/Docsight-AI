import axios from "axios";

const api = axios.create({
  baseURL:
    import.meta.env.VITE_API_URL ||
    "https://docsight-api-683710113441.europe-west3.run.app/api",
  headers: {
    "Content-Type": "application/json",
  },
});


// ======================================================
// HEALTH
// ======================================================

export const checkHealth = async () => {
  const response = await api.get("/health");
  return response.data;
};


// ======================================================
// DOCUMENT HISTORY
// ======================================================

export const getDocuments = async () => {
  const response = await api.get("/documents/history");
  return response.data;
};


// ======================================================
// DOCUMENT UPLOAD
// ======================================================

export const uploadDocument = async (
  file,
  onUploadProgress
) => {
  const formData = new FormData();

  formData.append(
    "file",
    file
  );

  const response = await api.post(
    "/documents/upload",
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      onUploadProgress,
    }
  );

  return response.data;
};


// ======================================================
// DOCUMENT DELETE
// ======================================================

export const deleteDocument = async (
  documentId
) => {
  if (!documentId) {
    throw new Error(
      "Document ID is required."
    );
  }

  const response = await api.delete(
    `/documents/${encodeURIComponent(
      documentId
    )}`
  );

  return response.data;
};


// ======================================================
// DOCUMENT PDF URL
// ======================================================

export const getDocumentFileUrl = (
  documentId
) => {
  if (!documentId) {
    return null;
  }

  return `${api.defaults.baseURL}/documents/${encodeURIComponent(
    documentId
  )}/file`;
};


// ======================================================
// ASK QUESTION
// ======================================================

export const askQuestion = async ({
  question,
  documentId,
  topK = 5,
}) => {
  const response = await api.post(
    "/questions/ask",
    {
      question,
      document_id: documentId || null,
      top_k: topK,
    }
  );

  return response.data;
};


// ======================================================
// CONVERSATION
// ======================================================

export const getConversation = async (
  documentId
) => {
  const response = await api.get(
    `/conversations/${encodeURIComponent(
      documentId
    )}`
  );

  return response.data;
};


export default api;