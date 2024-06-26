#include "../includes/lib.h"
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char *argv[])
{
  // open AD FIFO for writing
  int fd = open("tmp/ad_fifo", O_WRONLY);
  if (fd == -1)
  {
    perror("[ERROR] Couldn't open AD FIFO");
    return -1;
  }

  // get username
  char *username = get_username();
  if (username == NULL)
  {
    perror("[ERROR] Couldn't get username");
    return -1;
  }

  // create response fifo
  char path[100];
  snprintf(path, 100, "tmp/concordia/%s", username);

  umask(000);
  int r = mkfifo(path, 0666);
  if (r == -1)
  {
    perror("[ERROR] Couldn't create response FIFO");
    return -1;
  }

  // create message to send
  MESSAGE m;
  strncpy(m.sender, username, STRING_SIZE);
  strncpy(m.receiver, "server", STRING_SIZE);
  m.type = user_activate;
  strncpy(m.message, "", STRING_SIZE);
  m.timestamp = time(NULL);

  // send message
  r = write(fd, &m, sizeof(MESSAGE));
  if (r == -1)
  {
    perror("[ERROR] Couldn't send message");
    return -1;
  }

  // close main FIFO
  close(fd);

  // open response fifo for reading
  fd = open(path, O_RDONLY);
  if (fd == -1)
  {
    perror("[ERROR] Couldn't open response FIFO");
    return -1;
  }

  // wait for response
  MESSAGE response;
  int bytes_read = read(fd, &response, sizeof(MESSAGE));
  if (bytes_read == -1)
  {
    perror("[ERROR] Couldn't read response");
    return -1;
  }

  // close and remove response fifo
  close(fd);
  unlink(path);

  // check if user creation was successful
  if (strcmp(response.message, "failed") == 0)
  {
    printf("[ERROR] User creation failed\n");
    fflush(stdout);
    return -1;
  }

  // create sent directory
  char dir_path[100];
  snprintf(dir_path, 100, "concordia/%s/sent", username);

  r = mkdir(dir_path, 0700);
  if (r == -1)
  {
    perror("[ERROR] Couldn't create sent directory");
    return -1;
  }

  // create received directory
  sprintf(dir_path, "concordia/%s/received", username);

  r = mkdir(dir_path, 0700);
  if (r == -1)
  {
    perror("[ERROR] Couldn't create received directory");
    return -1;
  }

  printf("User '%s' activated.\n", username);
  fflush(stdout);

  return 0;
}
