'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { useDropzone } from 'react-dropzone';

interface FileUpload {
  id: string;
  name: string;
  status: 'uploading' | 'processing' | 'completed' | 'failed';
  progress: number;
  error?: string;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface Source {
  id: string;
  name: string;
  description: string;
}

interface Agent {
  id: string;
  name: string;
  description?: string;
}

export default function Home() {
  const [uploads, setUploads] = useState<FileUpload[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sources, setSources] = useState<Source[]>([]);
  const [showUpload, setShowUpload] = useState(false);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [currentAgent, setCurrentAgent] = useState<Agent | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load sources and agents on component mount
  useEffect(() => {
    loadSources();
    loadAgents();
  }, []);

  // Attach all existing sources to agent when agent is loaded
  useEffect(() => {
    if (currentAgent && sources.length > 0) {
      attachExistingSourcesToAgent();
    }
  }, [currentAgent, sources]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadSources = async () => {
    try {
      const response = await fetch('/api/sources/list');
      if (response.ok) {
        const data = await response.json();
        // The response might be an array directly or have a sources property
        const sourcesList = Array.isArray(data) ? data : (data.sources || []);
        setSources(sourcesList);
      }
    } catch (error) {
      console.error('Failed to load sources:', error);
    }
  };

  const loadAgents = async () => {
    try {
      const response = await fetch('/api/agents');
      if (response.ok) {
        const agentList = await response.json();
        setAgents(agentList);
        
        // If no current agent is selected, create or select the first one
        if (!currentAgent && agentList.length === 0) {
          await createDefaultAgent();
        } else if (!currentAgent && agentList.length > 0) {
          setCurrentAgent(agentList[0]);
        }
      }
    } catch (error) {
      console.error('Failed to load agents:', error);
    }
  };

  const attachExistingSourcesToAgent = async () => {
    if (!currentAgent) return;

    try {
      // Get currently attached sources
      const attachedResponse = await fetch(`/api/agents/${currentAgent.id}/sources`);
      const attachedSources = attachedResponse.ok ? await attachedResponse.json() : [];
      const attachedSourceIds = new Set(attachedSources.map((s: any) => s.id));

      // Attach any sources that aren't already attached
      for (const source of sources) {
        if (!attachedSourceIds.has(source.id)) {
          try {
            await fetch(`/api/agents/${currentAgent.id}/sources/${source.id}`, {
              method: 'PATCH',
            });
            console.log(`Attached source ${source.name} to agent`);
          } catch (error) {
            console.error(`Failed to attach source ${source.name}:`, error);
          }
        }
      }
    } catch (error) {
      console.error('Failed to attach existing sources:', error);
    }
  };

  const deleteSource = async (sourceId: string) => {
    try {
      const response = await fetch(`/api/sources/${sourceId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        // Refresh sources list after deletion
        await loadSources();
      } else if (response.status === 404) {
        // Document already deleted, just refresh the list
        await loadSources();
      } else {
        const errorData = await response.json();
        console.error('Failed to delete source:', errorData);
        setError('Failed to delete document');
      }
    } catch (error) {
      console.error('Failed to delete source:', error);
      setError('Failed to delete document');
    }
  };

  const createDefaultAgent = async () => {
    try {
      const response = await fetch('/api/agents', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: 'Context Assistant',
          description: 'An AI assistant that can answer questions based on uploaded documents.',
          agent_type: 'memgpt_agent',
          llm_config: {
            model: 'claude-3-5-sonnet-20241022', // Updated to latest Sonnet model
            model_endpoint_type: 'anthropic',
            model_endpoint: 'https://api.anthropic.com/v1/messages',
            context_window: 200000 // Increased context window for better document analysis
          },
          embedding_config: {
            embedding_model: 'sentence-transformers/all-MiniLM-L6-v2',
            embedding_endpoint_type: 'hugging-face',
            embedding_endpoint: 'http://localhost:8080',
            embedding_dim: 384,
            embedding_chunk_size: 8000
          },
          include_base_tools: true,
          tools: [
            "semantic_search_files",
            "archival_memory_search", 
            "conversation_search",
            "send_message"
          ],
          system: "You are a context-aware AI assistant that provides well-formatted, comprehensive responses by combining uploaded documents with your knowledge.\n\n**PROCESS FOR EVERY QUESTION:**\n\n1. **🔍 ALWAYS search first**: Use semantic_search_files to search uploaded documents\n2. **📋 Analyze context**: Note any relevant standards, preferences, or constraints from documents\n3. **🧠 Enhance with knowledge**: Fill gaps with your expertise while respecting document guidelines\n4. **📝 Format beautifully**: Structure your response for maximum readability\n\n**RESPONSE FORMATTING REQUIREMENTS:**\n\n✅ **Use clear headings** with ## and ###\n✅ **Add emojis** for visual appeal (🎯 📝 💡 ⚡ 🔧 etc.)\n✅ **Structure with bullets** and numbered lists\n✅ **Code blocks** with proper language tags\n✅ **Bold key terms** and **important concepts**\n✅ **Short paragraphs** (2-3 sentences max)\n✅ **Logical flow** from basic to advanced\n✅ **Clear sections** that are easy to scan\n\n**CONTENT STRUCTURE:**\n- Start with context acknowledgment if relevant\n- Provide practical, actionable information\n- Include code examples with explanations\n- End with recommendations or next steps\n\nMake every response visually appealing, easy to read, and professionally formatted!"
        }),
      });

      if (response.ok) {
        const newAgent = await response.json();
        setAgents([newAgent]);
        setCurrentAgent(newAgent);
      } else {
        const errorData = await response.json();
        console.error('Failed to create agent:', errorData);
        setError('Failed to create default agent');
      }
    } catch (error) {
      console.error('Failed to create agent:', error);
      setError('Failed to create default agent');
    }
  };

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading || !currentAgent) return;

    const messageContent = inputMessage.trim();
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: messageContent,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);
    setError(''); // Clear any previous errors

    try {
      const requestBody = {
        agent_id: currentAgent.id,
        messages: [{
          role: 'user',
          content: messageContent
        }]
      };

      console.log('Sending chat request:', requestBody);

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        throw new Error(`Chat request failed: ${response.statusText}`);
      }

      const data = await response.json();
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.choices?.[0]?.message?.content || 'Sorry, I could not generate a response.',
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error while processing your request. Please try again.',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    for (const file of acceptedFiles) {
      const uploadId = Math.random().toString(36).substr(2, 9);
      
      // Add file to uploads list
      setUploads(prev => [...prev, {
        id: uploadId,
        name: file.name,
        status: 'uploading',
        progress: 0
      }]);

      try {
        // Create source with correct embedding format - use Letta's embedding service
        // Make the name unique by adding timestamp to avoid conflicts
        const timestamp = Date.now();
        const uniqueName = `${file.name.replace(/\.[^/.]+$/, '')}_${timestamp}${file.name.match(/\.[^/.]+$/)?.[0] || ''}`;
        
        const sourceResponse = await fetch('/api/sources', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            name: uniqueName,
            description: `Uploaded file: ${file.name}`,
            embedding_config: {
              embedding_model: "sentence-transformers/all-MiniLM-L6-v2",
              embedding_endpoint_type: "hugging-face",
              embedding_endpoint: "http://localhost:8080",
              embedding_dim: 384,
              embedding_chunk_size: 8000
            }
          })
        });

        if (!sourceResponse.ok) {
          const errorData = await sourceResponse.json();
          throw new Error(`Failed to create source: ${sourceResponse.statusText} - ${JSON.stringify(errorData)}`);
        }

        const sourceData = await sourceResponse.json();
        
        // Update status to processing
        setUploads(prev => prev.map(upload => 
          upload.id === uploadId 
            ? { ...upload, status: 'processing', progress: 50 }
            : upload
        ));

        // Upload file
        const formData = new FormData();
        formData.append('file', file);

        const uploadResponse = await fetch(`/api/sources/${sourceData.id}/upload`, {
          method: 'POST',
          body: formData
        });

        if (!uploadResponse.ok) {
          const errorData = await uploadResponse.json();
          throw new Error(`Failed to upload file: ${uploadResponse.statusText} - ${JSON.stringify(errorData)}`);
        }

        const uploadData = await uploadResponse.json();

        // Update status to completed
        setUploads(prev => prev.map(upload => 
          upload.id === uploadId 
            ? { ...upload, status: 'completed', progress: 100 }
            : upload
        ));

        // Attach source to current agent for fast retrieval
        if (currentAgent) {
          try {
            await fetch(`/api/agents/${currentAgent.id}/sources/${sourceData.id}`, {
              method: 'PATCH',
            });
            console.log('Source attached to agent successfully');
          } catch (attachError) {
            console.error('Failed to attach source to agent:', attachError);
            // Continue anyway - source is still uploaded
          }
        }

        // Refresh sources list
        await loadSources();

      } catch (err) {
        console.error('Upload error:', err);
        setUploads(prev => prev.map(upload => 
          upload.id === uploadId 
            ? { ...upload, status: 'failed', error: err instanceof Error ? err.message : 'Unknown error' }
            : upload
        ));
        setError(err instanceof Error ? err.message : 'Upload failed');
      }
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'text/plain': ['.txt'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx']
    }
  });

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-gray-200">
          <h1 className="text-xl font-semibold text-gray-900">Letta Context Engine</h1>
          <p className="text-sm text-gray-500 mt-1">Upload & Chat with Documents</p>
        </div>

        {/* Upload Section */}
        <div className="p-4 border-b border-gray-200">
          <button
            onClick={() => setShowUpload(!showUpload)}
            className="w-full flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Upload Documents
          </button>
        </div>

        {/* Upload Area */}
        {showUpload && (
          <div className="p-4 border-b border-gray-200">
            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors ${
                isDragActive
                  ? 'border-blue-400 bg-blue-50'
                  : 'border-gray-300 hover:border-gray-400'
              }`}
            >
              <input {...getInputProps()} />
              <svg className="mx-auto h-8 w-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <p className="mt-2 text-sm text-gray-600">
                {isDragActive ? 'Drop files here' : 'Drag & drop or click to upload'}
              </p>
              <p className="text-xs text-gray-400 mt-1">PDF, TXT, DOC, DOCX</p>
            </div>

            {/* Upload Progress */}
            {uploads.length > 0 && (
              <div className="mt-4 space-y-2">
                {uploads.map((upload) => (
                  <div key={upload.id} className="bg-gray-50 rounded p-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="truncate">{upload.name}</span>
                      <span className="text-gray-500">{upload.progress}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-1 mt-1">
                      <div
                        className={`h-1 rounded-full transition-all duration-300 ${
                          upload.status === 'completed'
                            ? 'bg-green-400'
                            : upload.status === 'failed'
                            ? 'bg-red-400'
                            : 'bg-blue-400'
                        }`}
                        style={{ width: `${upload.progress}%` }}
                      ></div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Sources List */}
        <div className="flex-1 overflow-y-auto">
          <div className="p-4">
            <h3 className="text-sm font-medium text-gray-700 mb-3">Uploaded Documents</h3>
            {sources.length === 0 ? (
              <p className="text-sm text-gray-500">No documents uploaded yet</p>
            ) : (
              <div className="space-y-2">
                {sources.map((source) => (
                  <div key={source.id} className="bg-gray-50 rounded p-3 group">
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <h4 className="text-sm font-medium text-gray-900 truncate">{source.name}</h4>
                        <p className="text-xs text-gray-500 mt-1">{source.description}</p>
                      </div>
                      <button
                        onClick={() => deleteSource(source.id)}
                        className="ml-2 opacity-0 group-hover:opacity-100 transition-opacity p-1 text-red-500 hover:text-red-700 hover:bg-red-50 rounded"
                        title="Delete document"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="p-4 border-t border-gray-200">
            <div className="bg-red-50 border border-red-200 rounded-md p-3">
              <div className="flex">
                <svg className="h-4 w-4 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                <div className="ml-2">
                  <p className="text-xs text-red-800">{error}</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Chat Header */}
        <div className="bg-white border-b border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-medium text-gray-900">Chat with Documents</h2>
              <p className="text-sm text-gray-500">
                {sources.length} document{sources.length !== 1 ? 's' : ''} available
                {currentAgent && ` • Agent: ${currentAgent.name}`}
              </p>
            </div>
            <div className="flex items-center space-x-4 text-sm text-gray-500">
              <div className="flex items-center">
                <div className="w-2 h-2 bg-green-400 rounded-full mr-2"></div>
                Weaviate + Neo4j
              </div>
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <div className="text-center py-12">
              <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
              <h3 className="mt-2 text-sm font-medium text-gray-900">No messages yet</h3>
              <p className="mt-1 text-sm text-gray-500">
                {!currentAgent 
                  ? 'Setting up your assistant...' 
                  : sources.length === 0 
                    ? 'Upload documents first, then start asking questions.'
                    : 'Start a conversation by asking a question about your uploaded documents.'
                }
              </p>
            </div>
          ) : (
            messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-4xl px-4 py-3 rounded-lg shadow-sm ${
                    message.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-white border border-gray-200 text-gray-900'
                  }`}
                >
                  {message.role === 'assistant' ? (
                    <div 
                      className="prose prose-sm max-w-none text-gray-900"
                      dangerouslySetInnerHTML={{
                        __html: message.content
                          .replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold">$1</strong>')
                          .replace(/## (.*?)$/gm, '<h2 class="text-lg font-bold mt-4 mb-2 text-gray-800 border-b border-gray-200 pb-1">$1</h2>')
                          .replace(/### (.*?)$/gm, '<h3 class="text-md font-semibold mt-3 mb-2 text-gray-700">$1</h3>')
                          .replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre class="bg-gray-50 p-3 rounded-md border overflow-x-auto my-3"><code class="text-sm font-mono text-gray-800">$2</code></pre>')
                          .replace(/`([^`]+)`/g, '<code class="bg-gray-100 px-2 py-1 rounded text-sm font-mono text-gray-800">$1</code>')
                          .replace(/^\- (.*?)$/gm, '<li class="ml-4 mb-1">$1</li>')
                          .replace(/^\d+\. (.*?)$/gm, '<li class="ml-4 mb-1 list-decimal">$1</li>')
                          .replace(/(🔍|📋|🧠|📝|🎯|💡|⚡|🔧|🚀|📚|🔄|⚠️|❌|✅)/g, '<span class="mr-1">$1</span>')
                          .replace(/\n\n/g, '</p><p class="mb-3">')
                          .replace(/^([^<])/gm, '<p class="mb-3">$1')
                          .replace(/<\/p><p class="mb-3">(<h[23])/g, '</p>$1')
                          .replace(/<\/p><p class="mb-3">(<pre)/g, '</p>$1')
                          .replace(/<\/p><p class="mb-3">(<li)/g, '</p><ul class="mb-3 ml-4 space-y-1">$1')
                          .replace(/(<\/li>)<p class="mb-3">(<li)/g, '$1$2')
                          .replace(/(<\/li>)<p class="mb-3">(?!<li)/g, '$1</ul><p class="mb-3">')
                      }}
                    />
                  ) : (
                    <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                  )}
                  <p className="text-xs opacity-70 mt-2 text-right">
                    {message.timestamp.toLocaleTimeString()}
                  </p>
                </div>
              </div>
            ))
          )}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 text-gray-900 max-w-xs lg:max-w-md px-4 py-2 rounded-lg">
                <div className="flex items-center space-x-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600"></div>
                  <span className="text-sm">Thinking...</span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="bg-white border-t border-gray-200 p-4">
          <div className="flex space-x-4">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
              placeholder={!currentAgent ? "Setting up assistant..." : "Ask a question about your documents..."}
              className="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:text-gray-400"
              disabled={isLoading || !currentAgent}
            />
            <button
              onClick={sendMessage}
              disabled={!inputMessage.trim() || isLoading || !currentAgent}
              className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
