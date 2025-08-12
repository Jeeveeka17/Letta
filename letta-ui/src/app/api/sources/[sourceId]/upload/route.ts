import { NextRequest, NextResponse } from 'next/server';

const LETTA_API_KEY = 'sk-let-MGFmM2VkNjktN2I3Ni00MTg4LWJiODEtMjY5NjhjMTFmZWJjOmQ0YzgyOWZkLTRlZTgtNDJjMS1iNDIzLTVkODI2MjdjZjVlYw==';
const LETTA_BASE_URL = 'http://localhost:8283';

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ sourceId: string }> }
) {
  try {
    const { sourceId } = await params;
    const formData = await request.formData();
    
    // Forward the request to Letta server
    const response = await fetch(`${LETTA_BASE_URL}/v1/sources/${sourceId}/upload`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${LETTA_API_KEY}`,
      },
      body: formData,
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
