import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useRecoilValue } from 'recoil';

import { Alert, Box, Stack } from '@mui/material';

import Header from 'components/organisms/header';

import { useAuth } from 'hooks/auth';

import { projectSettingsState } from 'state/project';
import { userEnvState } from 'state/user';

type Props = {
  children: JSX.Element;
};

const Banner = ({}) => {
  return (
    <Stack
      alignItems="center"
      direction="row"
      className="image-banner"
      alignContent="center"
    >
      <Stack
        alignItems="center"
        direction="column"
        style={{ margin: '0 auto' }}
      >
        <h1>Data & Analytics Self-Assessment</h1>
        <h2>
          Powered by Onepoint's Data & Analytics Body of Knowledge and ChatGPT
        </h2>
      </Stack>
    </Stack>
  )
};

const Page = ({ children }: Props) => {
  const { isAuthenticated } = useAuth();
  const pSettings = useRecoilValue(projectSettingsState);
  const userEnv = useRecoilValue(userEnvState);
  const navigate = useNavigate();

  useEffect(() => {
    if (pSettings?.userEnv) {
      for (const key of pSettings.userEnv || []) {
        if (!userEnv[key]) navigate('/env');
      }
    }
    if (!isAuthenticated) {
      navigate('/login');
    }
  }, [pSettings, isAuthenticated, userEnv]);

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        width: '100%'
      }}
    >
      <Header />
      <Banner />
      {!isAuthenticated ? (
        <Alert severity="error">You are not part of this project.</Alert>
      ) : (
        children
      )}
    </Box>
  );
};

export default Page;
