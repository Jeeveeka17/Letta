import { NextRequest, NextResponse } from 'next/server';

const LETTA_API_KEY = 'sk-let-MGFmM2VkNjktN2I3Ni00MTg4LWJiODEtMjY5NjhjMTFmZWJjOmQ0YzgyOWZkLTRlZTgtNDJjMS1iNDIzLTVkODI2MjdjZjVlYw==';
const LETTA_BASE_URL = 'http://localhost:8283';

export async function GET(request: NextRequest) {
  try {
    // Forward the request to Letta server
    const response = await fetch(`${LETTA_BASE_URL}/v1/sources`, {
      method: 'GET',
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
    console.log('Sources response from Letta:', data);
    return NextResponse.json(data);
  } catch (error) {
    console.error('API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
