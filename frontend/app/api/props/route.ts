import { NextResponse } from 'next/server';

export async function GET(request: Request) {
  // This is a placeholder that will eventually fetch data from the Flask backend
  return NextResponse.json({ 
    message: 'Hello from the NBA Prop API!',
    data: []
  });
} 