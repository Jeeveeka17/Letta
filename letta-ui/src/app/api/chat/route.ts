import { NextRequest, NextResponse } from 'next/server';

const LETTA_API_KEY = 'sk-let-MGFmM2VkNjktN2I3Ni00MTg4LWJiODEtMjY5NjhjMTFmZWJjOmQ0YzgyOWZkLTRlZTgtNDJjMS1iNDIzLTVkODI2MjdjZjVlYw==';
const LETTA_BASE_URL = 'http://localhost:8283';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { agent_id, messages, message, agentId, isProcessingTrigger } = body;
    
    // Handle both old format (agent_id) and new format (agentId)
    const finalAgentId = agent_id || agentId;
    
    if (!finalAgentId) {
      return NextResponse.json(
        { error: 'agent_id or agentId is required' },
        { status: 400 }
      );
    }

    // Convert messages to Letta format
    let lettaRequest;
    
    if (message) {
      // New format (single message, possibly a processing trigger)
      lettaRequest = {
        messages: [
          {
            role: "user",
            content: message,
            name: "user"
          }
        ]
      };
    } else {
      // Old format (messages array)
      const userMessage = messages[messages.length - 1];
      lettaRequest = {
        messages: [
          {
            role: userMessage.role,
            content: userMessage.content,
            name: "user"
          }
        ]
      };
    }
    
    // Forward the request to Letta server
    const response = await fetch(`${LETTA_BASE_URL}/v1/agents/${finalAgentId}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${LETTA_API_KEY}`,
      },
      body: JSON.stringify(lettaRequest),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Letta server error:', response.status, errorText);
      return NextResponse.json(
        { error: `Letta server error: ${response.status} - ${errorText}` },
        { status: response.status }
      );
    }

    const data = await response.json();
    console.log('Letta chat response:', JSON.stringify(data, null, 2));
    
    // Convert Letta response to OpenAI-like format for compatibility
    let assistantContent = 'Sorry, I could not generate a response.';
    
    if (data.messages && Array.isArray(data.messages)) {
      // Try different ways to extract the response
      const responseTexts: string[] = [];
      
      data.messages.forEach((msg: any) => {
        // Skip basic assistant_message processing to avoid duplicates - we handle this at the end
        // Check for direct assistant content (fallback)
        if (msg.role === 'assistant' && msg.content && typeof msg.content === 'string') {
          responseTexts.push(msg.content);
        }
        
        // Check for function call responses (send_message tool)
        if (msg.tool_calls) {
          msg.tool_calls.forEach((call: any) => {
            if (call.function?.name === 'send_message' && call.function?.arguments) {
              try {
                const args = JSON.parse(call.function.arguments);
                if (args.message) {
                  responseTexts.push(args.message);
                }
              } catch (e) {
                console.error('Error parsing tool call arguments:', e);
              }
            }
          });
        }
        
        // Check for function responses
        if (msg.function_call_response?.function_return) {
          const returnValue = msg.function_call_response.function_return;
          if (typeof returnValue === 'string') {
            responseTexts.push(returnValue);
          }
        }
        
        // Check for tool return messages (like grep_files results)
        if (msg.message_type === 'tool_return_message' && msg.tool_return) {
          if (typeof msg.tool_return === 'string') {
            // Check if it's an error message - skip displaying errors, let LLM handle fallback
            if (!msg.tool_return.includes('Connection refused') && !msg.tool_return.includes('Errno') && !msg.tool_return.includes('Error')) {
              // Skip showing raw document chunks - let the LLM synthesize the information instead
              // The LLM will use this context to provide a proper contextual answer
              // Raw document display removed to avoid showing fragmented text
            }
          }
        }
        
        // Check for reasoning messages to provide context (should appear FIRST)
        if (msg.message_type === 'reasoning_message' && msg.reasoning) {
          if (typeof msg.reasoning === 'string' && msg.reasoning.length > 10) {
            // Only add reasoning if it doesn't contain "Analysis:" already
            if (!msg.reasoning.includes('🤔') && !msg.reasoning.includes('Analysis:')) {
              responseTexts.unshift(`🤔 **Analysis:** ${msg.reasoning}`);
            }
          }
        }
        
        // Check for assistant_message with comprehensive LLM responses (avoid duplicates)
        if (msg.message_type === 'assistant_message' && msg.content && typeof msg.content === 'string' && msg.content.length > 100) {
          // Skip if content already contains analysis formatting to avoid duplicates
          if (!msg.content.includes('🤔 **Analysis:**') && !msg.content.includes('💡 **Complete Answer:**')) {
            const formattedContent = `💡 **Complete Answer:**\n\n${msg.content}`;
            if (!responseTexts.some(text => text.includes(msg.content))) {
              responseTexts.push(formattedContent);
            }
          } else {
            // If content already has formatting, use it as-is
            if (!responseTexts.some(text => text.includes(msg.content))) {
              responseTexts.push(msg.content);
            }
          }
        }
      });
      
      // Filter out empty responses and join them
      const validResponses = responseTexts.filter(text => text && text.trim().length > 0);
      if (validResponses.length > 0) {
        assistantContent = validResponses.join('\n\n');
      }
      
      console.log('Extracted responses:', validResponses);
    }
    
    // Handle processing triggers silently (don't return response to user)
    if (isProcessingTrigger) {
      console.log('🔄 Processing trigger completed - document indexed for search');
      return NextResponse.json({ 
        success: true, 
        message: 'Document processing initiated',
        processed: true 
      });
    }

    const lettaResponse = {
      choices: [
        {
          message: {
            role: 'assistant',
            content: assistantContent
          }
        }
      ]
    };
    
    return NextResponse.json(lettaResponse);
  } catch (error) {
    console.error('API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
