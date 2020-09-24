const path = require('path');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const ManifestPlugin = require('webpack-manifest-plugin');
const { CleanWebpackPlugin } = require('clean-webpack-plugin');
const TerserJSPlugin = require('terser-webpack-plugin');
const OptimizeCSSAssetsPlugin = require('optimize-css-assets-webpack-plugin');

module.exports = function (env) {
    const production = env === 'production';
    return {
        context: path.resolve(__dirname, 'webserver', 'static'),
        entry: {
            common: ['./scripts/common.js'],
            datasets: ['./scripts/datasets.js'],
            similarity: ['./scripts/similarity.js'],
            global: ['./scripts/global.js'],
            homepage: ['./scripts/homepage.js'],
            profile: ['./scripts/profile.js'],
            stats: ['./scripts/stats.js'],
            main: ['./styles/main.less']
        },
        output: {
            chunkFilename: production ? '[name].[chunkhash].js' : '[name].js',
            filename: production ? '[name].[chunkhash].js' : '[name].js',
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
                                presets: ['@babel/preset-env', '@babel/preset-react'],
                                plugins: ['@babel/plugin-proposal-class-properties']
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
        optimization: {
            minimizer: [new TerserJSPlugin({}), new OptimizeCSSAssetsPlugin({})],
        },
        plugins: [
            new ManifestPlugin(),
            new MiniCssExtractPlugin({
                filename: production ? '[name].[chunkhash].css' : '[name].css',
                chunkFilename: production ? '[name].[chunkhash].css' : '[name].css'
            }),
            new CleanWebpackPlugin()
        ]
    }
};