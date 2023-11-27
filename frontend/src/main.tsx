import AppWrapper from 'AppWrapper';
import React from 'react';
import ReactDOM from 'react-dom/client';
import { RecoilRoot } from 'recoil';
import { UserbackProvider } from '@userback/react';

import './index.css';

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <RecoilRoot>
      <UserbackProvider token="34638|86705|Nm2GxChdROOCxxAsfWLXEPDoe">
        <AppWrapper />
      </UserbackProvider>
    </RecoilRoot>
  </React.StrictMode>
);
