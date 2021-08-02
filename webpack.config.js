const path = require('path');
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
        new ForkTsCheckerWebpackPlugin({
            typescript: {
                diagnosticOptions: {
                    semantic: true,
                    syntactic: true,
                },
                mode: "write-references",
            },
            // eslint: {
            //     // Starting the path with "**/" because of current dev/prod path discrepancy
            //     // In dev we bind-mount the source code to "/code/static" and in prod to "/static"
            //     // The "**/" allows us to ignore the folder structure and find source files in whatever CWD we're in.
            //     files: "scripts/**/*.{ts,tsx,js,jsx}",
            //     options: { fix: !production },
            // },
        }),
        new CleanWebpackPlugin()
    ]
    return {
        context: path.resolve(__dirname, 'webserver', 'static'),
        entry: {
            common: ['./scripts/common.ts'],
            datasets: ['./scripts/datasets.ts'],
            similarity: ['./scripts/similarity.ts'],
            global: ['./scripts/global.ts'],
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
        },
        plugins
    }
};