import { NextRequest, NextResponse } from 'next/server';

const LETTA_API_KEY = 'sk-let-MGFmM2VkNjktN2I3Ni00MTg4LWJiODEtMjY5NjhjMTFmZWJjOmQ0YzgyOWZkLTRlZTgtNDJjMS1iNDIzLTVkODI2MjdjZjVlYw==';
const LETTA_BASE_URL = 'http://localhost:8283';

// Attach source to agent
export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ agentId: string; sourceId: string }> }
) {
  try {
    const { agentId, sourceId } = await params;
    
    // Forward the request to Letta server
    const response = await fetch(`${LETTA_BASE_URL}/v1/agents/${agentId}/sources/attach/${sourceId}`, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${LETTA_API_KEY}`,
      },
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
    return NextResponse.json(data);
  } catch (error) {
    console.error('API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

