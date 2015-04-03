import time
import subprocess
import os.path
from django.conf import settings
import re
from graphite.logger import log
from graphite.storage import is_pattern, match_entries


class IndexSearcher:
  def __init__(self, index_dir):
    self.index_dir = index_dir
    self._last_mtimes = {}
    self._trees = {}

    for folder in settings.DATA_DIRS:
      index_file_name, index_path = self._index_file_name(folder)

      if not os.path.exists(index_path):
        open(index_path, 'w').close() # touch the file to prevent re-entry down this code path
        build_index_path = os.path.join(settings.GRAPHITE_BIN, "build-index.sh")
        retcode = subprocess.call([build_index_path, folder, index_path])
        if retcode != 0:
          log.exception("Couldn't build index file %s for %s" % (index_path, folder))
          raise RuntimeError("Couldn't build index file %s for %s" % (index_path, folder))
      self._last_mtimes[index_file_name] = 0
      self._trees[index_file_name] = (None, {}) # (data, children)
      log.info("[IndexSearcher] performing initial index load for %s" % folder)
      self.reload(folder)

  def _index_file_name(self, whisper_folder):
    index_file_name = (whisper_folder[1:] if whisper_folder[0] == os.sep else whisper_folder).replace(os.sep, ".")
    index_path = os.path.join(self.index_dir, index_file_name)

    return index_file_name, index_path

  def tree(self, folder):
    index_file_name, index_path = self._index_file_name(folder)

    current_mtime = os.path.getmtime(index_path)
    if current_mtime > self._last_mtimes[index_file_name]:
      log.info("[IndexSearcher] reloading stale index %s for %s, current_mtime=%s last_mtime=%s" %
               (index_path, folder, current_mtime, self._last_mtimes[index_file_name]))
      self.reload(folder)

    return self._trees[index_file_name]

  def reload(self, folder):
    index_file_name, index_path = self._index_file_name(folder)

    log.info("[IndexSearcher] reading index data from %s for %s" % (index_path, folder))
    t = time.time()
    total_entries = 0
    tree = (None, {}) # (data, children)
    for line in open(index_path):
      line = line.strip()
      if not line:
        continue

      branches = line.split('.')
      leaf = branches.pop()
      parent = None
      cursor = tree
      for branch in branches:
        if branch not in cursor[1]:
          cursor[1][branch] = (None, {}) # (data, children)
        parent = cursor
        cursor = cursor[1][branch]

      cursor[1][leaf] = (line, {})
      total_entries += 1

    self._trees[index_file_name] = tree
    self._last_mtimes[index_file_name] = os.path.getmtime(index_path)
    log.info("[IndexSearcher] index %s for %s reload took %.6f seconds (%d entries)" %
             (index_file_name, folder, time.time() - t, total_entries))

  def search(self, query, max_results=None, keep_query_pattern=False):
    query_parts = query.split('.')
    metrics_found = set()
    for folder in settings.DATA_DIRS:
      for result in self.subtree_query(self.tree(folder), query_parts):
        # Overlay the query pattern on the resulting paths
        if keep_query_pattern:
          path_parts = result['path'].split('.')
          result['path'] = '.'.join(query_parts) + result['path'][len(query_parts):]

        if result['path'] in metrics_found:
          continue
        yield result

        metrics_found.add(result['path'])
        if max_results is not None and len(metrics_found) >= max_results:
          return

  def subtree_query(self, root, query_parts):
    if query_parts:
      my_query = query_parts[0]
      if is_pattern(my_query):
        matches = [root[1][node] for node in match_entries(root[1], my_query)]
      elif my_query in root[1]:
        matches = [ root[1][my_query] ]
      else:
        matches = []

    else:
      matches = root[1].values()

    for child_node in matches:
      result = {
        'path' : child_node[0],
        'is_leaf' : bool(child_node[0]),
      }
      if result['path'] is not None and not result['is_leaf']:
        result['path'] += '.'
      yield result

      if query_parts:
        for result in self.subtree_query(child_node, query_parts[1:]):
          yield result

  def search_by_patterns(self, patterns, limit=100):
    regexes = [re.compile(p,re.I) for p in patterns]
    def matches(s):
      for regex in regexes:
        if regex.search(s):
          return True
      return False

    results = []

    for folder in settings.DATA_DIRS:
      index_file_name, index_path = self._index_file_name(folder)
      index_file = open(index_path)
      for line in index_file:
        if matches(line):
          results.append( line.strip() )
        if len(results) >= limit:
          break

      index_file.close()

      if len(results) >= limit:
        break

    return results

class SearchIndexCorrupt(StandardError):
  pass


searcher = IndexSearcher(settings.INDEX_DIR)
