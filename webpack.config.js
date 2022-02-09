const path = require('path');
const webpack = require('webpack');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const { WebpackManifestPlugin } = require("webpack-manifest-plugin");
const ForkTsCheckerWebpackPlugin = require("fork-ts-checker-webpack-plugin");
const { CleanWebpackPlugin } = require('clean-webpack-plugin');
const TerserJSPlugin = require('terser-webpack-plugin');
const OptimizeCSSAssetsPlugin = require('optimize-css-assets-webpack-plugin');

module.exports = function (env) {
    const production = env === 'production';
    const plugins = [
        new WebpackManifestPlugin(),
        new MiniCssExtractPlugin({
            filename: production ? '[name].[chunkhash].css' : '[name].css',
            chunkFilename: production ? '[name].[chunkhash].css' : '[name].css'
        }),
        new webpack.ProvidePlugin({
            $: 'jquery',
            jQuery: 'jquery',
        }),
        new ForkTsCheckerWebpackPlugin({
            typescript: {
                diagnosticOptions: {
                    semantic: true,
                    syntactic: true,
                },
                mode: "write-references",
            },
            eslint: {
                files: "scripts/**/*.{ts,tsx,js,jsx}",
                options: { fix: !production },
            },
        }),
        new CleanWebpackPlugin()
    ]
    return {
        context: path.resolve(__dirname, 'webserver', 'static'),
        entry: {
            bootstrap: ['./scripts/bootstrap.ts'],
            datasets: ['./scripts/datasets.tsx'],
            similarity: ['./scripts/similarity.ts'],
            homepage: ['./scripts/homepage.ts'],
            profile: ['./scripts/profile.ts'],
            stats: ['./scripts/stats.ts'],
            main: ['./styles/main.less']
        },
        output: {
            chunkFilename: production ? '[name].[chunkhash].js' : '[name].js',
            filename: production ? '[name].[chunkhash].js' : '[name].js',
            path: path.resolve(__dirname, 'webserver', 'static', 'build'),
            publicPath: '/static/build/'
        },
        mode: production ? 'production' : 'development',
        resolve: {
            extensions: ['.js', '.jsx', '.ts', '.tsx']
        },
        module: {
            rules: [
                {
                    test: /\.(js|ts)x?$/,
                    exclude: /node_modules/,
                    use: [
                        {
                            loader: 'babel-loader'
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
            splitChunks: {
                cacheGroups: {
                commons: {
                    name: 'common',
                    chunks: 'initial',
                    minChunks: 2,
                },
                },
            },
        },
        plugins
    }
};