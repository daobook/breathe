from __future__ import unicode_literals

from breathe.project import ProjectInfoFactory

try:
    from shlex import quote  # py3
except ImportError:
    from pipes import quote  # py2

import os


AUTOCFG_TEMPLATE = r"""
PROJECT_NAME     = "{project_name}"
OUTPUT_DIRECTORY = {output_dir}
GENERATE_LATEX   = NO
GENERATE_MAN     = NO
GENERATE_RTF     = NO
CASE_SENSE_NAMES = NO
INPUT            = {input}
ENABLE_PREPROCESSING = YES
QUIET            = YES
JAVADOC_AUTOBRIEF = YES
JAVADOC_AUTOBRIEF = NO
GENERATE_HTML = NO
GENERATE_XML = YES
ALIASES = rst="\verbatim embed:rst"
ALIASES += endrst="\endverbatim"
ALIASES += inlinerst="\verbatim embed:rst:inline"
{extra}
""".strip()


class ProjectData(object):
    "Simple handler for the files and project_info for each project"

    def __init__(self, auto_project_info, files):

        self.auto_project_info = auto_project_info
        self.files = files


class AutoDoxygenProcessHandle:
    def __init__(self, run_process, write_file, project_info_factory: ProjectInfoFactory):
        self.run_process = run_process
        self.write_file = write_file
        self.project_info_factory = project_info_factory

    def generate_xml(self, projects_source, doxygen_options, doxygen_aliases):

        project_files = {}

        # First collect together all the files which need to be doxygen processed for each project
        for project_name, file_structure in projects_source.items():

            folder = file_structure[0]
            contents = file_structure[1]

            auto_project_info = self.project_info_factory.create_auto_project_info(
                project_name, folder
            )

            project_files[project_name] = ProjectData(auto_project_info, contents)

        # Iterate over the projects and generate doxygen xml output for the files for each one into
        # a directory in the Sphinx build area
        for project_name, data in project_files.items():

            project_path = self.process(
                data.auto_project_info, data.files, doxygen_options, doxygen_aliases
            )

            project_info = data.auto_project_info.create_project_info(project_path)

            self.project_info_factory.store_project_info_for_auto(project_name, project_info)

    def process(self, auto_project_info, files, doxygen_options, doxygen_aliases):

        name = auto_project_info.name()
        cfgfile = "%s.cfg" % name

        full_paths = map(lambda x: auto_project_info.abs_path_to_source_file(x), files)

        options = "\n".join("%s=%s" % pair for pair in doxygen_options.items())
        aliases = "\n".join(
            f'ALIASES += {name}="{value}"' for name, value in doxygen_aliases.items()
        )

        cfg = AUTOCFG_TEMPLATE.format(
            project_name=name,
            output_dir=name,
            input=" ".join(full_paths),
            extra=f"{options}\n{aliases}",
        )

        build_dir = os.path.join(auto_project_info.build_dir(), "breathe", "doxygen")

        self.write_file(build_dir, cfgfile, cfg)

        # Shell-escape the cfg file name to try to avoid any issue where the name might include
        # malicious shell character - We have to use the shell=True option to make it work on
        # Windows. See issue #271
        self.run_process("doxygen %s" % quote(cfgfile), cwd=build_dir, shell=True)

        return os.path.join(build_dir, name, "xml")
