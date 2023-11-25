import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useRecoilValue, useRecoilState } from 'recoil';

import { Alert, Box, Stack } from '@mui/material';

import Header from 'components/organisms/header';

import { useAuth } from 'hooks/auth';

import { projectSettingsState } from 'state/project';
import { userEnvState } from 'state/user';

type Props = {
  children: JSX.Element;
};


// Added by Gil Fernandes
// eslint-disable-next-line @typescript-eslint/no-empty-pattern
function Banner () {
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
        <h1>Onepoint Data Wellness Companion™</h1>
        <h2>
          Powered by Onepoint’s Data & Analytics Body of Knowledge™ and ChatGPT <sub className='experimental'>Experimental</sub>
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
        flexDirection: 'row',
        width: '100%'
      }}
    >
      <div className='main-container'>
        <Header />
        <Banner />
        {!isAuthenticated ? (
          <Alert severity="error">You are not part of this project.</Alert>
        ) : (
          children
        )}
      </div>
    </Box>
  );
};

export default Page;
