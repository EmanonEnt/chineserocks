// 不使用 Edge Runtime，使用标准 Node.js
module.exports = (req, res) => {
  res.setHeader('Content-Type', 'text/plain; charset=utf-8');
  res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
  res.status(200).send('YlllsxOVRq4LBz');
};
