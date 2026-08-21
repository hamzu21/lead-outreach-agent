\ProvidesClass{resume}[2024/01/01 v1.0 Resume class]

\LoadClass[11pt,letterpaper]{article}

\RequirePackage[parfill]{parskip}
\RequirePackage{array}
\RequirePackage{ifthen}
\RequirePackage{hyperref}
\RequirePackage{xcolor}

\hypersetup{
    colorlinks=true,
    linkcolor=blue,
    filecolor=magenta,      
    urlcolor=blue,
}

\nofiles

\makeatletter

\def \name#1{\def\@name{#1}}
\def \@name{}

\def \address#1{
  \@ifundefined{@addressone}{
    \def \@addressone{#1}
  }{
    \def \@addresstwo{#1}
  }
}

\def \printname{
  \begingroup
    \centerline{\MakeUppercase{\Huge\bfseries \@name}}
    \nameskip
  \endgroup
}

\def \printaddress#1{
  \begingroup
    \centerline{#1}
  \endgroup
}

\let\ori@document=\document
\renewcommand{\document}{
  \ori@document
  \printname
  \@ifundefined{@addressone}{}{\printaddress{\@addressone}}
  \@ifundefined{@addresstwo}{}{\printaddress{\@addresstwo}}
}

\makeatother

\newenvironment{rSection}[1]{
  \sectionskip
  \MakeUppercase{\bfseries #1}
  \sectionlineskip
  \hrule
  \begin{list}{}{
    \setlength{\leftmargin}{0em}
  }
  \item[]
}{
  \end{list}
}

\def\nameskip{\vspace{5pt}}
\def\sectionskip{\vspace{8pt}}
\def\sectionlineskip{\vspace{3pt}}
