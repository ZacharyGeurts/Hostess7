/**
 * AmmoCode highlight — lightweight tokenizer (no Monaco, no telemetry).
 * g16 discern + web/config/data grammars · rich token classes via syntax.css
 */
(function (global) {
  "use strict";

  const C_KW =
    /\b(?:if|else|for|while|do|switch|case|break|return|struct|union|enum|typedef|static|const|volatile|void|int|char|float|double|long|short|unsigned|signed|sizeof|goto|continue|inline|restrict|_Alignas|_Alignof|_Atomic|_Bool|_Complex|_Generic|_Imaginary|_Noreturn|_Static_assert|_Thread_local|namespace|class|public|private|protected|virtual|override|template|typename|constexpr|noexcept|decltype|auto|nullptr|using|new|delete|this|throw|try|catch|operator|friend|explicit|mutable)\b/g;
  const PY_KW =
    /\b(?:def|class|if|elif|else|for|while|try|except|finally|with|as|import|from|return|yield|lambda|pass|break|continue|raise|async|await|True|False|None|and|or|not|in|is|global|nonlocal|match|case)\b/g;
  const NUM = /\b0x[0-9a-fA-F]+(?:u|ll|l|f|d)?\b|\b\d+\.?\d*(?:[eE][+-]?\d+)?[fFdD]?\b/g;
  const STR_DQ = /("(?:[^"\\]|\\.)*")/g;
  const STR_SQ = /('(?:[^'\\]|\\.)*')/g;
  const COM_C = /(\/\/[^\n]*|\/\*[\s\S]*?\*\/)/g;
  const COM_PY = /#[^\n]*/g;

  const RULES = {
    c: [
      [COM_C, "com"],
      [/(#[^\n]*)/g, "mac"],
      [C_KW, "kw"],
      [/\b(?:true|false|NULL)\b/g, "builtin"],
      [STR_DQ, "str"],
      [STR_SQ, "str"],
      [NUM, "num"],
      [/[+\-*/%=<>!&|^~?:]+/g, "op"],
    ],
    cxx: "c",
    cpp: "c",
    h: "c",
    objc: "c",
    python: [
      [COM_PY, "com"],
      [/("""[\s\S]*?"""|'''[\s\S]*?''')/g, "str2"],
      [STR_DQ, "str"],
      [STR_SQ, "str"],
      [PY_KW, "kw"],
      [/\bself\b/g, "self"],
      [/\b(?:int|float|str|bool|list|dict|tuple|set|bytes|object)\b/g, "ty"],
      [NUM, "num"],
      [/[+\-*/%=<>!&|^~@]+/g, "op"],
    ],
    rust: [
      [/\/\/[^\n]*|\/\*[\s\S]*?\*\//g, "com"],
      [/\b(?:fn|let|mut|if|else|match|for|while|loop|return|struct|enum|impl|trait|use|mod|pub|crate|self|Self|true|false|Some|None|Ok|Err|async|await|where|type|const|static|unsafe|dyn|ref|move|box|async|await|macro|union)\b/g, "kw"],
      [STR_DQ, "str"],
      [NUM, "num"],
      [/[+\-*/%=<>!&|^~]+/g, "op"],
    ],
    go: [
      [/\/\/[^\n]*/g, "com"],
      [/\b(?:func|package|import|var|const|type|struct|interface|if|else|for|range|switch|case|return|go|chan|map|defer|true|false|nil|make|new|len|cap|append)\b/g, "kw"],
      [/("[^"\\]*(?:\\.[^"\\]*)*"|`[^`]*`)/g, "str"],
      [NUM, "num"],
    ],
    zig: [
      [/\/\/[^\n]*/g, "com"],
      [/\b(?:fn|var|const|if|else|while|for|return|struct|enum|union|pub|comptime|try|catch|async|await|true|false|null|undefined|error|anytype|opaque|align|extern|volatile|allowzero|nosuspend|suspend|resume)\b/g, "kw"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    shell: [
      [/(#[^\n]*)/g, "com"],
      [/\b(?:if|then|else|fi|for|do|done|case|esac|function|return|export|local|while|until|select|in)\b/g, "kw"],
      [STR_DQ, "str"],
      [/('[^']*')/g, "str2"],
      [/\$\{?[a-zA-Z_][\w]*\}?/g, "var"],
    ],
    json: [
      [/("[^"\\]*(?:\\.[^"\\]*)*")(\s*:)/g, (m, s) => `<span class="fn">${esc(s)}</span>`],
      [/:\s*("[^"\\]*(?:\\.[^"\\]*)*")/g, "str"],
      [/\b(?:true|false|null)\b/g, "kw"],
      [/-?\d+\.?\d*(?:[eE][+-]?\d+)?/g, "num"],
    ],
    javascript: [
      [/\/\/[^\n]*|\/\*[\s\S]*?\*\//g, "com"],
      [/\b(?:function|const|let|var|if|else|for|while|return|class|extends|import|export|from|async|await|try|catch|new|this|true|false|null|undefined|typeof|instanceof|switch|case|break|continue|throw|default|yield|of|in|delete|void)\b/g, "kw"],
      [/("[^"\\]*(?:\\.[^"\\]*)*"|'[^'\\]*(?:\\.[^'\\]*)*'|`[^`]*`)/g, "str"],
      [NUM, "num"],
      [/[+\-*/%=<>!&|^~?:]+/g, "op"],
    ],
    typescript: "javascript",
    html: [
      [/<!--[\s\S]*?-->/g, "com"],
      [/(<\/?)([\w:-]+)/g, (m, a, b) => `${esc(a)}<span class="tag">${esc(b)}</span>`],
      [/(\s)([\w:-]+)(=)/g, (m, sp, a) => `${esc(sp)}<span class="attr">${esc(a)}</span>=`],
      [/("[^"]*"|'[^']*')/g, "str"],
    ],
    css: [
      [/\/\*[\s\S]*?\*\//g, "com"],
      [/(@[\w-]+)/g, "mac"],
      [/([.#]?[\w-]+)(\s*\{)/g, (m, sel) => `<span class="fn">${esc(sel)}</span>{`],
      [/([\w-]+)(\s*:)/g, (m, a) => `<span class="attr">${esc(a)}</span>:`],
      [/:\s*([^;}{]+)/g, (m, v) => `: <span class="val">${esc(v.trim())}</span>`],
      [/#[0-9a-fA-F]{3,8}\b/g, "num"],
    ],
    basic: [
      [/(REM\s[^\n]*)/gi, "com"],
      [/('[^\n']*)/g, "str"],
      [/\b(?:REM|GOTO|GOSUB|IF|THEN|ELSE|FOR|NEXT|WHILE|WEND|DIM|LET|PRINT|INPUT|READ|DATA|RESTORE|END|STOP|ON|DEF|FN|SUB|FUNCTION|RETURN|SELECT|CASE)\b/gi, "kw"],
      [NUM, "num"],
    ],
    fortran: [
      [/(![^\n]*|C[^\n]*)/gi, "com"],
      [/\b(?:PROGRAM|END|SUBROUTINE|FUNCTION|MODULE|USE|IMPLICIT|NONE|INTEGER|REAL|DOUBLE|COMPLEX|CHARACTER|LOGICAL|IF|THEN|ELSE|ENDIF|DO|CONTINUE|GO|TO|CALL|RETURN|PRINT|READ|WRITE|FORMAT|DATA|PARAMETER|COMMON|BLOCK|EQUIVALENCE)\b/gi, "kw"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    cobol: [
      [/\*[^\n]*/g, "com"],
      [/\b(?:IDENTIFICATION|DIVISION|PROGRAM-ID|DATA|PROCEDURE|WORKING-STORAGE|SECTION|PIC|VALUE|MOVE|PERFORM|IF|ELSE|END-IF|STOP|RUN|DISPLAY|ACCEPT|OPEN|CLOSE|READ|WRITE)\b/gi, "kw"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    pascal: [
      [(/\{[\s\S]*?\}|\(\*[\s\S]*?\*\))/g, "com"],
      [/\b(?:program|begin|end|var|const|type|procedure|function|if|then|else|for|to|downto|while|do|repeat|until|case|of|uses|unit|interface|implementation|record|array|string|integer|real|boolean|char)\b/gi, "kw"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    ini: [
      [/(;[^\n]*|#[^\n]*)/g, "com"],
      [/^\s*(\[[^\]]+\])/gm, "dec"],
      [/([\w.-]+)(\s*=)/g, (m, a) => `<span class="attr">${esc(a)}</span>=`],
      [/=\s*([^\n]+)/g, (m, v) => `= <span class="val">${esc(v.trim())}</span>`],
    ],
    diff: [
      [/^(\+\+\+[^\n]*|---[^\n]*|@@[^\n]*)/gm, "dec"],
      [/^(\+[^\n]*)/gm, "str"],
      [/^(-[^\n]*)/gm, "err"],
    ],
    csv: [
      [/("[^"]*")/g, "str"],
      [NUM, "num"],
    ],
    xml: [
      [/<!--[\s\S]*?-->/g, "com"],
      [/(<\/?)([\w:-]+)/g, (m, a, b) => `${esc(a)}<span class="tag">${esc(b)}</span>`],
      [/("[^"]*"|'[^']*')/g, "str"],
    ],
    plaintext: [],
    markdown: [
      [/(^#{1,6}\s.+$)/gm, "dec"],
      [/(`[^`]+`)/g, "str"],
      [/(\*\*[^*]+\*\*)/g, "fn"],
      [/(\[[^\]]+\]\([^)]+\))/g, "info"],
      [/^(?:---|\*\*\*|___)\s*$/gm, "com"],
    ],
    cmake: [
      [/(#[^\n]*)/g, "com"],
      [/\b(?:cmake_minimum_required|project|add_executable|add_library|target_link_libraries|set|if|else|endif|foreach|endforeach|include|find_package|option|message|install)\b/g, "kw"],
      [STR_DQ, "str"],
    ],
    asm: [
      [/([#;][^\n]*)/g, "com"],
      [/\b(?:mov|add|sub|mul|div|jmp|je|jne|call|ret|push|pop|xor|and|or|nop|lea|cmp|test|syscall|int)\b/gi, "kw"],
      [/\.[a-z_][\w]*/gi, "mac"],
      [/\b(?:rax|rbx|rcx|rdx|rsi|rdi|rsp|rbp|r8|r9|r10|r11|r12|r13|r14|r15|eax|ebx|ecx|edx)\b/gi, "ty"],
    ],
    toml: [
      [/(#[^\n]*)/g, "com"],
      [/^\s*(\[[^\]]+\])/gm, "dec"],
      [/([\w.-]+)(\s*=)/g, (m, k) => `<span class="fn">${esc(k)}</span>=`],
      [STR_DQ, "str"],
      [/\b(?:true|false)\b/g, "kw"],
      [NUM, "num"],
    ],
    yaml: [
      [/(#[^\n]*)/g, "com"],
      [/^(\s*[-*]\s+)/gm, "op"],
      [/([\w.-]+)(\s*:)/g, (m, k) => `<span class="fn">${esc(k)}</span>:`],
      [STR_DQ, "str"],
      [/\b(?:true|false|null|yes|no|on|off)\b/gi, "kw"],
      [NUM, "num"],
    ],
    sql: [
      [/--[^\n]*/g, "com"],
      [/\b(?:SELECT|FROM|WHERE|INSERT|INTO|UPDATE|DELETE|CREATE|TABLE|INDEX|JOIN|LEFT|RIGHT|INNER|OUTER|ON|AS|AND|OR|NOT|NULL|ORDER|BY|GROUP|HAVING|LIMIT|OFFSET|VALUES|SET|PRIMARY|KEY|FOREIGN|REFERENCES|UNIQUE|DEFAULT|BEGIN|COMMIT|ROLLBACK|WITH|DISTINCT|CASE|WHEN|THEN|ELSE|END|EXISTS|LIKE|IN|IS|CAST|COUNT|SUM|AVG)\b/gi, "kw"],
      [STR_DQ, "str"],
      [/'[^']*'/g, "str2"],
      [NUM, "num"],
    ],
    dockerfile: [
      [/(#[^\n]*)/g, "com"],
      [/^\s*(FROM|RUN|CMD|LABEL|EXPOSE|ENV|ADD|COPY|ENTRYPOINT|VOLUME|USER|WORKDIR|ARG|ONBUILD|STOPSIGNAL|HEALTHCHECK|SHELL)\b/gim, "kw"],
      [STR_DQ, "str"],
    ],
    ini: [
      [/(;[^\n]*|#[^\n]*)/g, "com"],
      [/^\s*(\[[^\]]+\])/gm, "dec"],
      [/([\w.-]+)(\s*=)/g, (m, k) => `<span class="fn">${esc(k)}</span>=`],
      [STR_DQ, "str"],
    ],
    xml: [
      [/<!--[\s\S]*?-->/g, "com"],
      [/(<\/?)([\w:-]+)/g, (m, a, b) => `${esc(a)}<span class="tag">${esc(b)}</span>`],
      [/([\w:-]+)(=)/g, (m, a) => `<span class="attr">${esc(a)}</span>=`],
      [/("[^"]*"|'[^']*')/g, "str"],
    ],
    graphql: [
      [/(#[^\n]*)/g, "com"],
      [/\b(?:query|mutation|subscription|fragment|on|type|interface|union|enum|input|schema|extend|implements|scalar|directive)\b/g, "kw"],
      [STR_DQ, "str"],
    ],
    ammolang: [
      [/(#[^\n]*)/g, "com"],
      [/@[\w]+(?:\s+[^\n]*)?/g, "mac"],
      [/(^|\s)(seq\s*[·.])(.*)$/i, (m, pre, op) => `${esc(pre)}<span class="dec">${esc(op)}</span>`],
      [/(^|\s)(par\s*[⊕+])(.*)$/i, (m, pre, op) => `${esc(pre)}<span class="dec">${esc(op)}</span>`],
      [/\b(?:combinator|seq|par|grow|scan|width|surface|collapse|gap|fill|boil|leaf|wire|exec|combine|bind|canonical|facet|depth|generations|product)\b/gi, "comb"],
      [/canonical:\w+/gi, "fn"],
      [/facet:\w+/gi, "ty"],
      [/\b(?:prog|g16|ironclad|band|chip|meta|declare|import|async|branch|call):\S+/gi, "ns"],
      [/("[^"\\]*(?:\\.[^"\\]*)*"|'[^'\\]*(?:\\.[^'\\]*)*')/g, "str"],
      [/(-?>|·|⊕|\+)/g, "op"],
      [NUM, "num"],
    ],
    field: [
      [/(#[^\n]*)/g, "com"],
      [/\b(?:field|plate|meld|gate|wave|die|belt|g16|nexus|queen|kilroy|entropy|truth|combinatorics|amplitude|depth|singular)\b/gi, "kw"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    glsl: [
      [/\/\/[^\n]*/g, "com"],
      [/#version\s+\d+/g, "mac"],
      [/\b(?:void|float|int|bool|vec2|vec3|vec4|mat2|mat3|mat4|uniform|attribute|varying|in|out|layout|precision|highp|mediump|lowp|if|else|for|while|return|struct|const|discard|true|false)\b/g, "kw"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    log: [
      [/\b(?:ERROR|ERR|FATAL|CRITICAL|WARN|WARNING|INFO|DEBUG|TRACE|ALERT)\b/g, "err"],
      [/\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}/g, "num"],
      [/\b(?:0x[0-9a-f]+|\d+)\b/gi, "num"],
      [/("[^"]*")/g, "str"],
    ],
    diff: [
      [/^@@.+@@$/gm, "diff-hunk"],
      [/^\+.*$/gm, "diff-add"],
      [/^-.*$/gm, "diff-del"],
    ],
    makefile: [
      [/(#[^\n]*)/g, "com"],
      [/^([\w./%-]+)(\s*:)/gm, (m, t) => `<span class="fn">${esc(t)}</span>:`],
      [/\$\{?[a-zA-Z_][\w]*\}?/g, "var"],
      [/\b(?:ifeq|ifneq|ifdef|ifndef|else|endif|include|export|unexport|vpath)\b/g, "kw"],
    ],
    java: [
      [/\/\/[^\n]*|\/\*[\s\S]*?\*\//g, "com"],
      [/\b(?:public|private|protected|class|interface|extends|implements|import|package|void|int|long|float|double|boolean|char|byte|short|if|else|for|while|return|new|this|super|static|final|abstract|synchronized|throws|try|catch|finally|throw|enum|var|record|true|false|null)\b/g, "kw"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    csharp: [
      [/\/\/[^\n]*|\/\*[\s\S]*?\*\//g, "com"],
      [/\b(?:using|namespace|class|struct|interface|enum|public|private|protected|internal|static|readonly|const|void|int|string|bool|float|double|decimal|if|else|for|foreach|while|return|new|this|base|async|await|try|catch|finally|throw|var|true|false|null)\b/g, "kw"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    kotlin: [
      [/\/\/[^\n]*|\/\*[\s\S]*?\*\//g, "com"],
      [/\b(?:fun|val|var|class|object|interface|package|import|if|else|when|for|while|return|try|catch|finally|throw|true|false|null|is|in|as|data|sealed|open|override|companion|suspend|async|await)\b/g, "kw"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    swift: [
      [/\/\/[^\n]*|\/\*[\s\S]*?\*\//g, "com"],
      [/\b(?:func|var|let|class|struct|enum|protocol|extension|import|if|else|guard|switch|case|for|while|return|try|catch|throw|async|await|true|false|nil|self|Self|inout|mutating|static|public|private|internal)\b/g, "kw"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    scala: [
      [/\/\/[^\n]*|\/\*[\s\S]*?\*\//g, "com"],
      [/\b(?:def|val|var|class|object|trait|extends|with|import|package|if|else|match|case|for|while|return|try|catch|finally|throw|true|false|null|lazy|implicit|override|sealed|final)\b/g, "kw"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    dart: [
      [/\/\/[^\n]*|\/\*[\s\S]*?\*\//g, "com"],
      [/\b(?:import|library|class|extends|implements|mixin|enum|void|int|double|bool|String|if|else|for|while|return|async|await|try|catch|finally|throw|true|false|null|const|final|var|new)\b/g, "kw"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    nim: [
      [/#.*$/gm, "com"],
      [/\/\*[\s\S]*?\*\//g, "com"],
      [/\b(?:proc|func|method|template|macro|type|object|enum|import|from|if|elif|else|case|of|for|while|return|discard|true|false|nil|var|let|const|when|block|try|except|finally|raise)\b/g, "kw"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    d: [
      [/\/\/[^\n]*|\/\*[\s\S]*?\*\//g, "com"],
      [/\b(?:module|import|class|struct|interface|enum|function|void|int|uint|long|float|double|bool|if|else|foreach|for|while|return|try|catch|finally|throw|true|false|null|auto|const|immutable|shared|static|public|private|protected)\b/g, "kw"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    ada: [
      [/--[^\n]*/g, "com"],
      [/\b(?:procedure|function|package|with|use|type|record|array|range|if|then|else|elsif|end|loop|while|for|return|begin|null|true|false|private|limited|access|constant|pragma)\b/gi, "kw"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    haskell: [
      [/--[^\n]*/g, "com"],
      [/\{-[\s\S]*?-\}/g, "com"],
      [/\b(?:module|import|data|type|newtype|class|instance|where|let|in|if|then|else|case|of|do|return|True|False|Maybe|Just|Nothing|IO|forall|qualified)\b/g, "kw"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    ocaml: [
      [/\(\*[\s\S]*?\*\)/g, "com"],
      [/\b(?:let|in|fun|match|with|type|module|open|include|if|then|else|rec|and|or|true|false|exception|raise|try|begin|end|struct|sig|object|method|val|mutable|external)\b/g, "kw"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    clojure: [
      [/;[^\n]*/g, "com"],
      [/\b(?:defn|def|let|fn|if|do|loop|recur|try|catch|throw|ns|require|use|import|true|false|nil|and|or|not|when|cond|case|->|->>)\b/g, "kw"],
      [/:"[^"]*"/g, "str2"],
      [STR_DQ, "str"],
      [/:[\w!?+-]+/g, "ty"],
      [NUM, "num"],
    ],
    lisp: [
      [/;[^\n]*/g, "com"],
      [/\b(?:defun|defmacro|lambda|let|if|cond|progn|setq|quote|funcall|apply|loop|return|nil|t|car|cdr|cons)\b/gi, "kw"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    elixir: [
      [/#.*$/gm, "com"],
      [/\b(?:def|defp|defmodule|import|alias|require|use|if|else|unless|case|cond|with|for|fn|do|end|true|false|nil|when|raise|try|rescue|catch|throw|spawn|receive)\b/g, "kw"],
      [/:"[^"]*"/g, "str2"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    erlang: [
      [/%[^\n]*/g, "com"],
      [/\b(?:module|export|import|record|define|ifdef|ifndef|if|case|of|end|fun|receive|when|try|catch|throw|true|false|begin|query)\b/g, "kw"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    prolog: [
      [/%[^\n]*/g, "com"],
      [/\b(?:module|use_module|:-|true|fail|not|is|mod|div|assert|retract|cut|if|then|else|forall|exists)\b/gi, "kw"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    ruby: [
      [/#.*$/gm, "com"],
      [/\b(?:def|class|module|end|if|elsif|else|unless|case|when|while|until|for|do|return|yield|begin|rescue|ensure|raise|true|false|nil|self|super|attr_reader|attr_writer|include|extend|require)\b/g, "kw"],
      [STR_DQ, "str"],
      [/:'[^']*'/g, "str2"],
      [NUM, "num"],
    ],
    perl: [
      [/#.*$/gm, "com"],
      [/\b(?:sub|my|our|local|package|use|require|if|elsif|else|unless|while|until|for|foreach|return|die|warn|true|false|undef|shift|push|pop|qw|q|qq)\b/g, "kw"],
      [STR_DQ, "str"],
      [/q\{[^}]*\}/g, "str2"],
      [NUM, "num"],
    ],
    php: [
      [/\/\/[^\n]*|#[^\n]*|\/\*[\s\S]*?\*\//g, "com"],
      [/\b(?:function|class|interface|trait|namespace|use|public|private|protected|static|return|if|else|elseif|foreach|for|while|try|catch|finally|throw|new|true|false|null|echo|print|require|include)\b/g, "kw"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    lua: [
      [/--[^\n]*/g, "com"],
      [/\b(?:function|local|end|if|then|else|elseif|for|while|repeat|until|return|break|true|false|nil|and|or|not|in|goto)\b/g, "kw"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    r: [
      [/#.*$/gm, "com"],
      [/\b(?:function|if|else|for|while|repeat|return|TRUE|FALSE|NULL|NA|Inf|NaN|library|require|source|<-|->)\b/g, "kw"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    julia: [
      [/#.*$/gm, "com"],
      [/\b(?:function|struct|mutable|abstract|type|module|import|using|if|else|elseif|for|while|return|try|catch|finally|throw|true|false|nothing|end|begin|const|global|local|macro)\b/g, "kw"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    matlab: [
      [/%[^\n]*/g, "com"],
      [/\b(?:function|end|if|elseif|else|for|while|switch|case|otherwise|return|true|false|classdef|properties|methods|global|persistent)\b/gi, "kw"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    fortran: [
      [/[cC!].*$/gm, "com"],
      [/\b(?:program|module|subroutine|function|end|if|then|else|elseif|do|while|return|integer|real|double|precision|character|logical|complex|dimension|allocatable|parameter|implicit|none|use|only|select|case)\b/gi, "kw"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    cobol: [
      [/\*[^\n]*/g, "com"],
      [/\b(?:IDENTIFICATION|DIVISION|PROGRAM-ID|DATA|PROCEDURE|WORKING-STORAGE|LOCAL-STORAGE|LINKAGE|SECTION|PIC|VALUE|MOVE|PERFORM|UNTIL|IF|ELSE|END-IF|STOP|RUN|DISPLAY|ACCEPT|OPEN|CLOSE|READ|WRITE|DELETE|REWRITE)\b/gi, "kw"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    pascal: [
      [/\{[\s\S]*?\}/g, "com"],
      [/\(\*[\s\S]*?\*\)/g, "com"],
      [/\/\/[^\n]*/g, "com"],
      [/\b(?:program|unit|interface|implementation|uses|begin|end|var|const|type|record|array|of|procedure|function|if|then|else|repeat|until|while|for|to|downto|case|mod|div|true|false|nil|inherited|override|virtual|abstract)\b/gi, "kw"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    turbo_pascal: "pascal",
    delphi: "pascal",
    modula2: [
      [/\(\*[\s\S]*?\*\)/g, "com"],
      [/\b(?:MODULE|FROM|IMPORT|EXPORT|BEGIN|END|VAR|CONST|TYPE|PROCEDURE|FUNCTION|IF|THEN|ELSE|ELSIF|WHILE|REPEAT|UNTIL|FOR|TO|BY|LOOP|EXIT|RETURN|RECORD|ARRAY|OF|SET|WITH|CASE)\b/g, "kw"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    basic: [
      [/(REM[^\n]*|'[^\n]*)/gi, "com"],
      [/\b(?:DIM|AS|IF|THEN|ELSE|ENDIF|FOR|TO|NEXT|WHILE|WEND|DO|LOOP|GOTO|GOSUB|RETURN|END|SUB|FUNCTION|PRINT|INPUT|LET|DATA|READ|RESTORE|ON|ERROR|RESUME|SELECT|CASE|CONST|SHARED|STATIC|DECLARE|DEF|TYPE)\b/gi, "kw"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    qbasic: "basic",
    quickbasic: "basic",
    freebasic: "basic",
    visual_basic: [
      [/(REM[^\n]*|'[^\n]*)/gi, "com"],
      [/\b(?:Sub|End Sub|Function|End Function|Dim|As|If|Then|Else|ElseIf|End If|For|To|Next|While|Wend|Do|Loop|Select|Case|End Select|Public|Private|Const|Static|Option|Explicit|True|False|Nothing|Me|Set|Call|Return|GoTo|On Error|Resume)\b/gi, "kw"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    vba: "visual_basic",
    verilog: [
      [/\/\/[^\n]*/g, "com"],
      [/\/\*[\s\S]*?\*\//g, "com"],
      [/\b(?:module|endmodule|input|output|inout|wire|reg|logic|assign|always|initial|if|else|case|endcase|for|while|begin|end|posedge|negedge|parameter|localparam|generate|endgenerate|function|task)\b/g, "kw"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    forth: [
      [/\([^)]*\)/g, "com"],
      [/\\[^\n]*/g, "com"],
      [/\b(?::|variable|constant|create|does>|if|then|else|begin|until|while|repeat|do|loop|leave|exit|true|false)\b/gi, "kw"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    smalltalk: [
      [/"[^"]*"/g, "str"],
      [/\b(?:self|super|true|false|nil|ifTrue:|ifFalse:|whileTrue:|whileFalse:|do:|collect:|select:|reject:|and:|or:|not|new|initialize|subclass:)\b/g, "kw"],
      [/#\w+/g, "ty"],
      [NUM, "num"],
    ],
    snobol: [
      [/\*[^\n]*/g, "com"],
      [/\b(?:end|return|goto|succeed|fail|abort|output|input|define|prototype)\b/gi, "kw"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    apl: [
      [/⍝[^\n]*/g, "com"],
      [/←|→|⌶|⍴|⍳|⍵|⍺|∇|¯|×|÷|⌈|⌊|∧|∨|≠|≤|≥/g, "op"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    algol: [
      [/\/\/[^\n]*/g, "com"],
      [/\b(?:begin|end|if|then|else|for|step|until|while|do|procedure|integer|real|boolean|array|comment|go to|own|value)\b/gi, "kw"],
      [STR_DQ, "str"],
      [NUM, "num"],
    ],
    plaintext: [],
  };

  RULES.cpp = RULES.cxx = RULES.objc = RULES.h = RULES.c;
  RULES.cs = RULES.csharp;
  RULES.ts = RULES.typescript = RULES.javascript;
  RULES.js = RULES.javascript;
  RULES.sh = RULES.bash = RULES.zsh = RULES.shell;
  RULES.ps1 = RULES.shell;
  RULES.yml = RULES.yaml;
  RULES.md = RULES.markdown;
  RULES.f90 = RULES.f95 = RULES.f03 = RULES.f = RULES.for = RULES.fortran;
  RULES.gpy = RULES.python;
  RULES.vert = RULES.frag = RULES.comp = RULES.glsl;
  RULES.wat = RULES.wasm = RULES.asm;
  RULES.aml = RULES.ammolang;
  RULES.pas = RULES.pp = RULES.tp = RULES.tpu = RULES.pascal;
  RULES.bi = RULES.fb = RULES.fbi = RULES.qb = RULES.qbi = RULES.qbs = RULES.freebasic;
  RULES.bas = RULES.vb = RULES.vbs = RULES.vba;
  RULES.sv = RULES.v = RULES.verilog;
  RULES.sc = RULES.scala;
  RULES.hs = RULES.lhs = RULES.haskell;
  RULES.ml = RULES.mli = RULES.ocaml;
  RULES.clj = RULES.cljc = RULES.cljs = RULES.clojure;
  RULES.ex = RULES.exs = RULES.elixir;
  RULES.erl = RULES.hrl = RULES.erlang;
  RULES.rb = RULES.ruby;
  RULES.pl = RULES.pm = RULES.perl;
  RULES.jl = RULES.julia;
  RULES.kt = RULES.kts = RULES.kotlin;
  RULES.cbl = RULES.cob = RULES.cobol;
  RULES.fs = RULES.fth = RULES.forth;
  RULES.st = RULES.smalltalk;
  RULES.sno = RULES.snobol;
  RULES.alg = RULES.algol;
  RULES.apl = RULES.apl;
  RULES.adb = RULES.ads = RULES.ada;
  RULES.mm = RULES.objc;
  RULES.lisp = RULES.lsp = RULES.cl = RULES.lisp;
  RULES.pro = RULES.prolog;
  RULES.m = RULES.matlab;
  RULES.dpr = RULES.dfm = RULES.delphi;

  const EXT_MAP = {
    ".py": "python", ".pyw": "python", ".gpy": "python",
    ".rs": "rust", ".go": "go", ".zig": "zig",
    ".c": "c", ".h": "c", ".cpp": "cxx", ".cc": "cxx", ".cxx": "cxx", ".hpp": "cxx", ".hh": "cxx", ".ixx": "cxx", ".C": "cxx",
    ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "typescript", ".jsx": "typescript",
    ".json": "json", ".jsonc": "json",
    ".html": "html", ".htm": "html", ".xhtml": "html",
    ".css": "css", ".scss": "css", ".less": "css",
    ".md": "markdown", ".markdown": "markdown", ".tex": "markdown",
    ".sh": "shell", ".bash": "shell", ".zsh": "shell", ".ps1": "shell",
    ".cmake": "cmake", ".s": "asm", ".S": "asm", ".asm": "asm", ".wat": "asm", ".wasm": "asm",
    ".toml": "toml", ".yaml": "yaml", ".yml": "yaml",
    ".sql": "sql", ".dockerfile": "dockerfile", ".ini": "ini", ".cfg": "ini", ".conf": "ini",
    ".xml": "xml", ".svg": "xml",
    ".graphql": "graphql", ".gql": "graphql",
    ".fld": "field", ".aml": "ammolang",
    ".vert": "glsl", ".frag": "glsl", ".comp": "glsl", ".glsl": "glsl",
    ".log": "log", ".diff": "diff", ".patch": "diff",
    ".mk": "makefile",
    ".java": "java", ".kt": "kotlin", ".kts": "kotlin",
    ".cs": "csharp", ".swift": "swift", ".scala": "scala", ".sc": "scala",
    ".dart": "dart", ".nim": "nim", ".d": "d",
    ".adb": "ada", ".ads": "ada",
    ".hs": "haskell", ".lhs": "haskell",
    ".ml": "ocaml", ".mli": "ocaml",
    ".clj": "clojure", ".cljc": "clojure", ".cljs": "clojure",
    ".lisp": "lisp", ".lsp": "lisp", ".cl": "lisp",
    ".ex": "elixir", ".exs": "elixir",
    ".erl": "erlang", ".hrl": "erlang",
    ".rb": "ruby", ".pl": "perl", ".pm": "perl",
    ".php": "php", ".lua": "lua", ".r": "r", ".jl": "julia",
    ".m": "matlab", ".f": "fortran", ".f90": "fortran", ".f95": "fortran", ".f03": "fortran", ".for": "fortran",
    ".cbl": "cobol", ".cob": "cobol",
    ".pas": "pascal", ".pp": "pascal", ".tp": "turbo_pascal", ".tpu": "turbo_pascal",
    ".dpr": "delphi", ".dfm": "delphi",
    ".mod": "modula2",
    ".bas": "basic", ".bi": "freebasic", ".fb": "freebasic", ".fbi": "freebasic",
    ".qb": "qbasic", ".qbi": "qbasic", ".qbs": "quickbasic",
    ".vb": "vba", ".vba": "vba", ".vbs": "vba", ".inc": "vba",
    ".sv": "verilog", ".v": "verilog", ".vhdl": "plaintext",
    ".fs": "forth", ".fth": "forth",
    ".st": "smalltalk", ".sno": "snobol",
    ".apl": "apl", ".alg": "algol",
    ".mm": "objc", ".pro": "prolog",
    ".bib": "plaintext",
  };

  function esc(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function span(cls, text) {
    return `<span class="${cls}">${esc(text)}</span>`;
  }

  function resolveLang(lang) {
    let key = String(lang || "plaintext").toLowerCase();
    const seen = new Set();
    while (key && !seen.has(key)) {
      seen.add(key);
      const rule = RULES[key];
      if (!rule) return "plaintext";
      if (Array.isArray(rule)) return key;
      if (typeof rule === "string") {
        key = rule;
        continue;
      }
      return "plaintext";
    }
    return "plaintext";
  }

  function mergeExtensions(extMap) {
    if (!extMap || typeof extMap !== "object") return { ...EXT_MAP };
    for (const [ext, lang] of Object.entries(extMap)) {
      if (ext && lang) EXT_MAP[String(ext).toLowerCase()] = String(lang).toLowerCase();
    }
    return EXT_MAP;
  }

  function langFromPath(path) {
    const m = String(path || "").toLowerCase().match(/(\.[a-z0-9]+)$/i);
    return m ? EXT_MAP[m[1].toLowerCase()] || "plaintext" : "plaintext";
  }

  function hasHighlight(lang) {
    const resolved = resolveLang(lang);
    const rules = RULES[resolved];
    return Array.isArray(rules) && rules.length > 0;
  }

  function highlightLine(line, lang) {
    const resolved = resolveLang(lang);
    const rules = Array.isArray(RULES[resolved]) ? RULES[resolved] : [];
    if (!rules.length) return esc(line) + "\n";
    let out = esc(line);
    for (const rule of rules) {
      const re = rule[0];
      const cls = rule[1];
      if (typeof cls === "function") {
        out = out.replace(re, cls);
        continue;
      }
      out = out.replace(re, (m) => span(cls, m));
    }
    return out + "\n";
  }

  function highlight(text, lang) {
    const lines = String(text || "").split("\n");
    return lines.map((ln) => highlightLine(ln, lang)).join("");
  }

  function gutterLines(text) {
    const n = Math.max(1, (String(text || "").match(/\n/g) || []).length + 1);
    const rows = [];
    for (let i = 1; i <= n; i += 1) rows.push(String(i));
    return rows.join("\n");
  }

  const api = {
    highlight,
    highlightLine,
    gutterLines,
    langFromPath,
    resolveLang,
    mergeExtensions,
    hasHighlight,
    RULES,
    EXT_MAP,
  };
  global.AmmoCodeHighlight = api;
  global.QueenCodeHighlight = api;
})(typeof globalThis !== "undefined" ? globalThis : window);