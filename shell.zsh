# Source this file from zsh.
[[ ${CODE_PUSH_TAGS_LOADED:-0} == 1 ]] && return 0
if (( $+functions[git] || $+aliases[git] )); then
  return 1
fi
typeset -g CODE_PUSH_TAGS_LOADED=1
typeset -g CODE_PUSH_TAGS_ROOT=${${(%):-%N}:A:h}
typeset -g CODE_PUSH_TAGS_PYTHON=${commands[python3]}
git() {
  local -a scan
  scan=("$@")
  local is_push=0
  while (( ${#scan} )); do
    case "$scan[1]" in
      -C|-c|--git-dir|--work-tree|--namespace|--config-env)
        (( ${#scan} >= 2 )) || break
        scan=("${scan[@]:2}") ;;
      --git-dir=*|--work-tree=*|--namespace=*|--config-env=*|--exec-path=*|--super-prefix=*)
        scan=("${scan[@]:1}") ;;
      --no-pager|--paginate|-p|-P|--bare|--no-replace-objects|--literal-pathspecs|--glob-pathspecs|--noglob-pathspecs|--icase-pathspecs|--no-optional-locks|--no-lazy-fetch)
        scan=("${scan[@]:1}") ;;
      push) is_push=1; break ;;
      *) break ;;
    esac
  done
  command git "$@"
  local git_status=$?
  if (( git_status == 0 && is_push && ${#CODE_PUSH_TAGS_PYTHON} )); then
    "$CODE_PUSH_TAGS_PYTHON" "$CODE_PUSH_TAGS_ROOT/push_tags.py" play --event push </dev/null >/dev/null 2>&1 &!
  fi
  return $git_status
}
