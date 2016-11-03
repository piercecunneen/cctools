/*
Copyright (C) 2016- The University of Notre Dame
This software is distributed under the GNU General Public License.
See the file COPYING for details.
*/

#ifndef MAKEFLOW_CACHE_H
#define MAKEFLOW_CACHE_H

#include "dag.h"
#include "dag_file.h"
#include "dag_node.h"
#include "sha1.h"
#include "list.h"

/* Given a node, generate the cache_id from the input files and command */
void makeflow_cache_generate_id(struct dag_node *n, char *command, struct list*inputs);

/* Preserves the current node within the caching directory
   The source makeflow file, ancestor node cache_ids, and the output files are cached */
void makeflow_cache_populate(struct dag *d, struct dag_node *n, struct list *outputs, struct batch_job_info *info);

/* Returns true if a node has been preserved within the caching directory*/
int makeflow_cache_is_preserved(struct dag *d, struct dag_node *n, char *command, struct list *inputs, struct list *outputs);

/* */
int makeflow_cache_copy_preserved_files(struct dag *d, struct dag_node *n, struct list *outputs);

void makeflow_write_run_info(struct dag *d, struct dag_node *n, char *cache_path, struct batch_job_info *info);

void makeflow_write_file_checksum(struct dag *d, struct dag_file *f, char *job_cache_path);

void generate_file_cache_id(struct dag_file *f);

void write_descendant_link(struct dag *d, struct dag_node *current_node, struct dag_node *ancestor_node);

void write_ancestor_links(struct dag *d, struct dag_node *current_node, struct dag_node *ancestor_node);
#endif
