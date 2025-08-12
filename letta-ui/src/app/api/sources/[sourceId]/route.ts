import { NextRequest, NextResponse } from 'next/server';

const LETTA_API_KEY = 'sk-let-MGFmM2VkNjktN2I3Ni00MTg4LWJiODEtMjY5NjhjMTFmZWJjOmQ0YzgyOWZkLTRlZTgtNDJjMS1iNDIzLTVkODI2MjdjZjVlYw==';
const LETTA_BASE_URL = 'http://localhost:8283';

// Delete source
export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ sourceId: string }> }
) {
  try {
    const { sourceId } = await params;
    
    // Forward the request to Letta server
    const response = await fetch(`${LETTA_BASE_URL}/v1/sources/${sourceId}`, {
      method: 'DELETE',
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

    // Return success (DELETE might return empty response)
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

