import { grey } from 'theme/palette';

import Typography from '@mui/material/Typography';

interface Props {
  timestamp: number | string;
}

const MessageTime = ({ timestamp }: Props) => {
  if (!timestamp) return null;
  
  const dateOptions: Intl.DateTimeFormatOptions = {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  };
  const date = new Date(timestamp).toLocaleTimeString(undefined, dateOptions);
  return (
    <Typography className="message-date" lineHeight="24px" color={grey[500]} fontSize="11px">
      {date}
    </Typography>
  );
};

export { MessageTime };
