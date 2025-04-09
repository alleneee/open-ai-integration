/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,
    // 配置环境变量
    env: {
        NEXT_PUBLIC_API_BASE_URL: 'http://localhost:8000',
    },
    // 如果后端API部署在不同域，需要配置rewrites或CORS
    // 例如，将/api代理到后端:
    async rewrites() {
        return [
            {
                source: '/api/:path*',
                destination: 'http://localhost:8000/api/:path*', // 你的后端API地址
            },
        ]
    },
};

export default nextConfig; 