import { NextRequest, NextResponse } from 'next/server';

const LETTA_API_KEY = 'sk-let-MGFmM2VkNjktN2I3Ni00MTg4LWJiODEtMjY5NjhjMTFmZWJjOmQ0YzgyOWZkLTRlZTgtNDJjMS1iNDIzLTVkODI2MjdjZjVlYw==';
const LETTA_BASE_URL = 'http://localhost:8283';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { agent_id, messages } = body;
    
    if (!agent_id) {
      return NextResponse.json(
        { error: 'agent_id is required' },
        { status: 400 }
      );
    }

    // Convert messages to Letta format
    const userMessage = messages[messages.length - 1];
    const lettaRequest = {
      messages: [
        {
          role: userMessage.role,
          content: userMessage.content,
          name: "user"
        }
      ]
    };
    
    // Forward the request to Letta server
    const response = await fetch(`${LETTA_BASE_URL}/v1/agents/${agent_id}/messages`, {
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
        // Check for assistant_message type with content (PRIORITY - this should come first)
        if (msg.message_type === 'assistant_message' && msg.content && typeof msg.content === 'string') {
          responseTexts.push(msg.content);
        }
        
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
            // Check if it's an error message
            if (msg.tool_return.includes('Connection refused') || msg.tool_return.includes('Errno')) {
              responseTexts.push(`⚠️ **Search Error**: ${msg.tool_return}\n\n💡 **LLM Response**: I'll provide an answer based on my general knowledge since the document search encountered an issue.`);
            } else {
              // Format tool results nicely
              const formattedResult = msg.tool_return
                .replace(/Found \d+ matches in \d+ files for pattern: '[^']*'\n=+\n\n/g, '')
                .replace(/=== [^:]+:(\d+) ===/g, '\n**Line $1:**')
                .replace(/>\s*(\d+):\s*/g, '$1: ')
                .trim();
              responseTexts.push(`📄 **Found in your document:**\n\n${formattedResult}`);
            }
          }
        }
        
        // Check for reasoning messages to provide context
        if (msg.message_type === 'reasoning_message' && msg.reasoning) {
          if (typeof msg.reasoning === 'string' && msg.reasoning.length > 10) {
            responseTexts.push(`🤔 **Analysis:** ${msg.reasoning}`);
          }
        }
        
        // Check for assistant_message with comprehensive LLM responses (should be last to get priority)
        if (msg.message_type === 'assistant_message' && msg.content && typeof msg.content === 'string' && msg.content.length > 100) {
          // This is likely the main LLM response, give it higher priority
          responseTexts.unshift(`💡 **Complete Answer:**\n\n${msg.content}`);
        }
      });
      
      // Filter out empty responses and join them
      const validResponses = responseTexts.filter(text => text && text.trim().length > 0);
      if (validResponses.length > 0) {
        assistantContent = validResponses.join('\n\n');
      }
      
      console.log('Extracted responses:', validResponses);
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
