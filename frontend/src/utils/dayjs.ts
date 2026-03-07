import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import 'dayjs/locale/zh-cn'

dayjs.locale('zh-cn')
dayjs.extend(utc)
dayjs.extend(timezone)

export const SHANGHAI_TZ = 'Asia/Shanghai'

export default dayjs
