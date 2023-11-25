import { ReactMarkdown } from 'react-markdown/lib/react-markdown';
import { useRecoilValue } from 'recoil';
import remarkGfm from 'remark-gfm';

import { Box, Link } from '@mui/material';

import { Code } from '@chainlit/components';

import { projectSettingsState } from 'state/project';
import rehypeRaw from "rehype-raw";

const WelcomeScreen = () => {
  const pSettings = useRecoilValue(projectSettingsState);

  if (!pSettings?.markdown) {
    return <Box flexGrow={1} />;
  }

  return (
    <Box pt={2} overflow="auto" flexGrow={1}>
      <Box
        id="welcome-screen"
        sx={{
          maxWidth: '60rem',
          width: '100%',
          m: 'auto',
          color: 'text.primary',
          lineHeight: '25px',
          fontSize: '1rem',
          fontFamily:
            '-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif,Apple Color Emoji,Segoe UI Emoji',
          display: 'flex',
          flexDirection: 'column'
        }}
      >
        {pSettings?.markdown ? (
          <ReactMarkdown
            className="markdown-body"
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeRaw]}
            components={{
              a: ({ children, ...props }) => (
                <Link {...props} target="_blank">
                  {children}
                </Link>
              ),
              code: ({ ...props }) => <Code {...props} />
            }}
          >
            {pSettings?.markdown}
          </ReactMarkdown>
        ) : null}
      </Box>
    </Box>
  );
};

export default WelcomeScreen;
