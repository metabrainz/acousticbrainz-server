var _ = require('lodash');
var fs = require('fs');
var gulp = require('gulp');
var less = require('gulp-less');
var path = require('path');
var rev = require('gulp-rev');
var source = require('vinyl-source-stream');
var streamify = require('gulp-streamify');
var through2 = require('through2');
var Q = require('q');
var yarb = require('yarb');

var devMode = String(process.env.NODE_ENV) !== 'production';

const CACHED_BUNDLES = new Map();
const STATIC_DIR = path.resolve(__dirname, '../static');
const BUILD_DIR = path.resolve(STATIC_DIR, 'build');
const STYLES_DIR = path.resolve(STATIC_DIR, 'styles');
const SCRIPTS_DIR = path.resolve(STATIC_DIR, 'scripts');

const revManifestPath = path.resolve(BUILD_DIR, 'rev-manifest.json');
const revManifest = {};

if (fs.existsSync(revManifestPath)) {
  _.assign(revManifest, JSON.parse(fs.readFileSync(revManifestPath)));
}

function writeManifest() {
  fs.writeFileSync(revManifestPath, JSON.stringify(revManifest));
}

function writeResource(stream) {
  var deferred = Q.defer();

  stream
    .on('error', function (error) {
      deferred.reject(error);
    })
    .pipe(streamify(rev()))
    .pipe(gulp.dest(BUILD_DIR))
    .pipe(rev.manifest())
    .pipe(through2.obj(function (chunk, encoding, callback) {
      _.assign(revManifest, JSON.parse(chunk.contents));
      callback();
    }))
    .on('finish', function () {
      deferred.resolve();
    });

  return deferred.promise;
}

function buildStyles(callback) {
  return writeResource(
    gulp.src(path.resolve(STYLES_DIR, '*.less'))
    .pipe(less({
      rootpath: '/static/',
      relativeUrls: true,
      plugins: [
        new (require('less-plugin-clean-css'))({compatibility: 'ie8'})
      ]
    }))
  ).done(callback);
}

function transformBundle(bundle) {
  bundle.transform('babelify');
  bundle.transform('envify', {global: true});
  return bundle;
}

function runYarb(resourceName, callback) {
  if (resourceName in CACHED_BUNDLES) {
    return CACHED_BUNDLES.get(resourceName);
  }

  var bundle = transformBundle(yarb(path.resolve(SCRIPTS_DIR, resourceName), {
    debug: devMode // Enable sourcemaps if in development mode
  }));

  if (callback) {
    callback(bundle);
  }

  CACHED_BUNDLES.set(resourceName, bundle);
  return bundle;
}

function bundleScripts(b, resourceName) {
  return b.bundle().on('error', console.log).pipe(source(resourceName));
}

function writeScript(b, resourceName) {
  return writeResource(bundleScripts(b, resourceName));
}

function buildScripts() {
  var commonBundle = runYarb('common.js');
  var datasetsBundle = runYarb('datasets.js', function (b) {
    b.external(commonBundle);
  });
  var statsBundle = runYarb('stats.js');
  var homepageBundle = runYarb('homepage.js');
  var profileBundle = runYarb('profile.js');
  var similarityBundle = runYarb('similarity.js');

  return Q.all([
    writeScript(commonBundle, 'common.js'),
    writeScript(datasetsBundle, 'datasets.js'),
    writeScript(statsBundle, 'stats.js'),
    writeScript(homepageBundle, 'homepage.js'),
    writeScript(profileBundle, 'profile.js'),
    writeScript(similarityBundle, 'similarity.js')
  ]).then(writeManifest);
}

gulp.task('styles', function () {
  return buildStyles(writeManifest);
});
gulp.task('scripts', buildScripts);

gulp.task('watch', ['styles', 'scripts'], function () {

  gulp.watch(path.resolve(STATIC_DIR, '**/*.less'), ['styles']);

  function rebundle(b, resourceName, file) {
    var rebuild = false;

    switch (file.event) {
      case 'add':
        rebuild = true;
        break;
      case 'change':
      case 'unlink':
        rebuild = b.has(file.path);
        break;
    }

    if (rebuild) {
      process.stdout.write(`Rebuilding ${resourceName} (${file.event}: ${file.path}) ... `);
      writeScript(b, resourceName).done(function () {
        writeManifest();
        process.stdout.write('done.\n');
      });
    }
  }

  let watch = require('gulp-watch');
  watch(path.resolve(SCRIPTS_DIR, '**/*.js'), function (file) {
    CACHED_BUNDLES.forEach(function (bundle, resourceName) {
      rebundle(bundle, resourceName, file);
    });
  });
});

gulp.task('clean', function () {
  var fileRegex = /^([a-z\-]+)-[a-f0-9]+\.(js|css)$/;

  fs.readdirSync(BUILD_DIR).forEach(function (file) {
    if (fileRegex.test(file) && revManifest[file.replace(fileRegex, '$1.$2')] !== file) {
      fs.unlinkSync(path.resolve(BUILD_DIR, file));
    }
  });
});

gulp.task('default', ['styles', 'scripts']);
