const path = require('path');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const ManifestPlugin = require('webpack-manifest-plugin');

const production = process.env.NODE_ENV === 'production';

let config = {
    context: path.resolve(__dirname, 'webserver', 'static'),
    entry: {
        common: ['./scripts/common.js'],
        datasets: ['./scripts/datasets.js'],
        global: ['./scripts/global.js'],
        homepage: ['./scripts/homepage.js'],
        profile: ['./scripts/profile.js'],
        stats: ['./scripts/stats.js'],
        main: ['./styles/main.less']
    },
    output: {
        chunkFilename: production ? 'js/[name].[chunkhash].js' : 'js/[name].js',
        filename: production ? 'js/[name].[chunkhash].js' : 'js/[name].js',
        path: path.resolve(__dirname, 'webserver', 'static', 'build'),
        publicPath: '/static/build/'
    },
    mode: production ? 'production' : 'development',
    module: {
        rules: [
            {
                test: /\.jsx?$/,
                exclude: /node_modules/,
                use: [
                    {
                        loader: 'babel-loader',
                        options: {
                            presets: ['react']
                        }
                    }
                ],
            },
            {
                test: /\.less$/,
                use: [
                    {loader: MiniCssExtractPlugin.loader},
                    {loader: 'css-loader'},
                    {
                        loader: 'less-loader',
                        // Set 'paths' to use the less resolver not the webpack one
                        // https://www.npmjs.com/package/less-loader#less-resolver
                        // Fixes issue where we @import url(https://googlefont)
                        options: {
                            paths: [path.resolve(__dirname, 'node_modules')],
                        }
                    }
                ]
            }
        ],
    },
    plugins: [new ManifestPlugin(), new MiniCssExtractPlugin()]
};

module.exports = config;
