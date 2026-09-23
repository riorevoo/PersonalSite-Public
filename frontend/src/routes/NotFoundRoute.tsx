import { PageNotice } from '../components/PageNotice'

/** Any address the site does not have. */
export function NotFoundRoute() {
  return <PageNotice heading="NOT FOUND">There is nothing at this address.</PageNotice>
}
