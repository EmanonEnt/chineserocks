export default function middleware(request) {
  const url = new URL(request.url);
  
  if (url.pathname === '/MP_verify_YlllsxOVRq4LBz.txt') {
    return new Response('YlllsxOVRq4LBz', {
      status: 200,
      headers: {
        'Content-Type': 'text/plain; charset=utf-8',
        'Cache-Control': 'no-cache, no-store, must-revalidate'
      }
    });
  }
  
  return NextResponse.next();
}

export const config = {
  matcher: '/MP_verify_YlllsxOVRq4LBz.txt'
};
