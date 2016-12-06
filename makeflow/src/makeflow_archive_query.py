import hashlib
import os
import sys
import getopt


paths_to_jobs = {}

class SimpleDag(object):
  def __init__(self):
    self.name = "dag"
    self.root_nodes = []

class SimpleDagJob(object):
  def __init__(self, path, local_path = ""):
    self.archived_path = path
    self.local_path = local_path
    paths_to_jobs[self.archived_path] = self
    self.command = ""
    self.batch_job_info = {}
    self.input_files= []
    self.output_files= []
    self.ancestors = []
    self.descendants = []
    self.recover_run_info()
    self.create_input_output_files()
    self.recover_ancestors()
    self.recover_descendants()

  def add_input_file(self, file_path):
    self.input_files.append(SimpleDagFile(file_path))

  def add_output_file(self, file_path):
    self.output_files.append(SimpleDagFile(file_path, self.command))


  def create_input_output_files(self):
    input_file_directories = os.path.join(self.archived_path, "input_files")
    input_file_paths = [os.path.realpath(os.path.join(input_file_directories, f_path)) for f_path in os.listdir(input_file_directories)]

    output_file_dir = os.path.join(self.archived_path, "outputs")
    output_file_paths = [os.path.join(output_file_dir, f_path) for f_path in os.listdir(output_file_dir)]

    for o_path in output_file_paths:
      self.add_output_file(o_path)

    for i_path in input_file_paths:
      self.add_input_file(i_path)

  def recover_ancestors(self):
    path = os.path.join(self.archived_path, "ancestors")
    try:
      with open(path, "r") as f:
        line = f.readline().rstrip()
        while line:
          archive_prefix = line[0:2]
          ancestor_path = os.path.realpath(os.path.join(self.archived_path, "../../", archive_prefix, line))
          if ancestor_path in paths_to_jobs:
            self.ancestors.append(paths_to_jobs[ancestor_path])
          else:
            new_dag_job = SimpleDagJob(ancestor_path)
            self.ancestors.append(new_dag_job)
            paths_to_jobs[ancestor_path] = new_dag_job
          line = f.readline().rstrip()
    except IOError:
      pass

  def recover_descendants(self):
    descendant_dir = os.path.join(self.archived_path, "descendants")
    descendant_job_paths = [os.path.realpath(os.path.join(self.archived_path,"descendants", path)) for path in os.listdir(descendant_dir)]
    for descendant_path in descendant_job_paths:
      if descendant_path in paths_to_jobs:
        self.descendants.append(paths_to_jobs[descendant_path])
      else:
        new_dag_job = SimpleDagJob(descendant_path)
        self.descendants.append(new_dag_job)
        paths_to_jobs[descendant_path] = new_dag_job

  def recover_run_info(self):
    run_info_path = os.path.join(self.archived_path, "run_info")
    with open(run_info_path, "r") as f:
      self.command = f.readline().rstrip()
      self.wrapped_command = f.readline().rstrip()
      self.batch_job_info['submitted'] = int(f.readline().rstrip())
      self.batch_job_info['started'] = int(f.readline().rstrip())
      self.batch_job_info['finished'] = int(f.readline().rstrip())
      self.batch_job_info['exited_normally'] = int(f.readline().rstrip())
      self.batch_job_info['exit_code'] = int(f.readline().rstrip())
      self.batch_job_info['exit_signal'] = int(f.readline().rstrip())
  def print_immediate_inputs(self):
    for f in self.input_files:
      print f.file_path
    print ''

  def print_all_inputs(self):
    queue= [(self, 0)]
    while len(queue) > 0:
      node, distance = queue.pop()
      print distance
      node.print_immediate_inputs()
      for child in node.ancestors:
        queue.append((child, distance + 1))

  def print_immediate_outputs(self):
    for f in self.output_files:
      print f.file_path
    print ''

  def print_all_outputs(self):
    visted = {}
    queue= [(self, 0)]
    visted[self.archived_path] = 1
    while len(queue) > 0:
      node, distance = queue.pop()
      print distance
      node.print_immediate_outputs()
      for child in node.descendants:
        if child.archived_path not in visted:
          queue.append((child, distance + 1))
          visted[child.archived_path] = 1

  def print_job(self):
    print "file:{}".format(self.local_path)
    print "Created by job archived at path:{}".format(self.archived_path)
    print "Command used to create this file:{}".format(self.wrapped_command)
    print "makeflow file archived at path:{}".format(get_makeflow_path(self))
    print "Inputs:"
    self.print_immediate_inputs()

class SimpleDagFile(object):
  def __init__(self, file_path, command = ""):
    self.command = ""
    self.file_path = file_path
    self.file_name = file_path.split(',')[-1]


def recreate_job(job_path, local_):

  new_dag_job = SimpleDagJob(job_path, local_)
  node = new_dag_job
  return node

def get_makeflow_path(node):
  while len(node.ancestors) != 0:
    node = node.ancestors[0]
  return os.path.join(node.archived_path, "source_makeflow")

def get_dag_roots(dag_node):
  nodes_seen = {}
  root_nodes = []
  search(dag_node, nodes_seen, root_nodes)
  return root_nodes


def search(dag_node, nodes_seen, root_nodes):
  nodes_seen[dag_node.path] = 1
  if len(dag_node.ancestors) == 0:
    root_nodes.append(dag_node)
  for node in dag_node.ancestors:
    if node.path not in nodes_seen:
      search(node, nodes_seen, root_nodes)
  for node in dag_node.descendants:
    if node.path not in nodes_seen:
      search(node, nodes_seen, root_nodes)


def usage():
  print """usage: makeflow_recover [options] <file>
  options:
    --info                   print out basic info about the specified file and the associated job
    -i, --inputs             list immediate input files required to create file
    --inputs-all             list both immediate input files and all other files that the specified file relied on directly or indirectly
    -h, --help               print this message
    -o, --outputs            list sibling output files
    --outputs-all            list both sibling output files and all other files that relied directly or indirectly on the specified file
    --path=<path_to_archive>   path to search for the makeflow archive (use if when preserving the makeflow you specified a archive path)

  """
  sys.exit(1)

def parse_args():
  arg_map = {'inputs': False, 'outputs': False, "file": None, "inputs-all": False,
            "outputs-all": False, "info": False, "path": "/tmp/makeflow.archive.{}".format(os.geteuid())}
  try:
    opts, args = getopt.getopt(sys.argv[1:], ":hio", ['help', 'inputs', 'outputs', 'inputs-all', 'outputs-all', 'info', 'path='])
  except getopt.GetoptError as err:
    print str(err)
    usage()
  for o, a in opts:
    if o in ("-h", '--help'):
      usage()
    elif o in ("-o", "--outputs"):
      arg_map['outputs'] = True
    elif o in ("-i", "--inputs"):
      arg_map['inputs'] = True
    elif o in ("--outputs-all"):
      arg_map['outputs-all'] = True
    elif o in ("--inputs-all"):
      arg_map['inputs-all'] = True
    elif o in ("--info"):
      arg_map['info'] = True
    elif o in ("--path"):
      arg_map['path'] = a
    else:
      assert False, "unhandled option"
  if len(opts) == 0 or (len(opts) == 1 and opts[0][0] == '--path'):
    arg_map['info'] = True
  arg_map['file'] = args[0]
  if not arg_map['file'] or not os.path.isfile(arg_map['file']):
    print "Cannot find file {}".format(arg_map['file'])
    usage()
  return arg_map


if __name__ == "__main__":
  arguments = parse_args()

  sha1_hash = hashlib.sha1()
  file_name = arguments['file']
  with open(file_name, "r") as f:
    line = f.readline()
    while line:
      sha1_hash.update(line)
      line = f.readline()
  hex_digest = sha1_hash.hexdigest()
  file_path = os.path.join(arguments['path'], "files", hex_digest[0:2], hex_digest[2:])
  print file_path
  if os.path.islink(file_path):
    resolved_job_path = os.path.realpath(file_path)
    node = recreate_job(resolved_job_path, file_name)
    if arguments['inputs']:
      print "Inputs"
      node.print_immediate_inputs()
    if arguments['outputs']:
      print "Outputs"
      node.print_immediate_outputs()
    if arguments['inputs-all']:
      print "Inputs-all"
      node.print_all_inputs()
    if arguments['outputs-all']:
      print "Outputs-all"
      node.print_all_outputs()
    if arguments['info']:
      node.print_job()
  else:
    print "File has not been archived"
