% Resume Class File
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

%----------------------------------------------------------------------------------------
%	HEADINGS COMMANDS
%----------------------------------------------------------------------------------------

\def \name#1{\def\@name{#1}}
\def \@name{}

\def \address#1{
  @ifundefined{@addressone}{
    \def \@addressone{#1}
  }{
    \def \@addresstwo{#1}
  }
}

\def \printname{
  \begingroup
    \hfil{\MakeUppercase{\Huge\bfseries \@name}}\hfil
    \nameskip\break
  \endgroup
}

\def \printaddress#1{
  \begingroup
    \def \def@address{#1}
    \hfil{\def@address}\hfil
    \nameskip\break
  \endgroup
}

\let\ori@document=\document
\renewcommand{\document}{
  \ori@document
  \printname
  @ifundefined{@addressone}{}{\printaddress{\@addressone}}
  @ifundefined{@addresstwo}{}{\printaddress{\@addresstwo}}
}

%----------------------------------------------------------------------------------------
%	SECTION FORMATTING
%----------------------------------------------------------------------------------------

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
