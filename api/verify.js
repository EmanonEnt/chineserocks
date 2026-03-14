export const config = {
  runtime: 'edge',
};

export default function handler(request) {
  const content = 'YlllsxOVRq4LBz';
  
  return new Response(content, {
    status: 200,
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
      'Cache-Control': 'public, max-age=0, must-revalidate',
    },
  });
}
