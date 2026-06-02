import streamlit as st
from google import genai
from google.genai import types
import json, io, csv, re, time, base64, html
import urllib.request, urllib.error
from datetime import datetime

# ── Scoring Lookup Table (từ file Excel Thang điểm) ────────────────────────────
SCORING_LOOKUP = {"Trình độ học vấn":{"A":{"desc":"Không yêu cầu kiến thức phổ thông và khả năng đọc/viết. Có thể cần được đào tạo cho các công việc chân tay, thủ công, đơn giản.","score":12.0},"B":{"desc":"Hoàn thành cấp tiểu học, có kiến thức phổ thông cơ bản với kỹ năng đọc, viết và thực hiện các phép tính đơn giản, ví dụ: cộng, trừ, nhân, chia.","score":16.0},"C":{"desc":"Hoàn thành cấp THCS và có khả năng viết văn bản hoặc thực hiện các phép tính nâng cao hơn, ví dụ: phân số, phần trăm và thập phân.","score":22.0},"D":{"desc":"Hoàn thành cấp THPT và có khả năng gõ văn bản, tài liệu bằng máy tính,…","score":29.0},"E":{"desc":"Hoàn thành (các) khóa học/ khóa đào tạo nghề từ 03 tháng đến dưới 01 năm","score":38.0},"F1":{"desc":"Tốt nghiệp Trung cấp nghề chuyên ngành bất kỳ","score":43.0},"F2":{"desc":"Tốt nghiệp Trung cấp nghề (các) chuyên ngành cụ thể","score":50.0},"G1":{"desc":"Tốt nghiệp Cao đẳng chuyên ngành bất kỳ","score":57.0},"G2":{"desc":"Tốt nghiệp Cao đẳng (các) chuyên ngành cụ thể","score":66.0},"H1":{"desc":"Tốt nghiệp Đại học chuyên ngành bất kỳ","score":76.0},"H2":{"desc":"Tốt nghiệp Đại học (các) chuyên ngành cụ thể","score":87.0},"I1":{"desc":"Tốt nghiệp đại học và lớp bồi dưỡng, nâng cao nghiệp vụ/văn bằng 2 của ngành khác","score":100.0},"I2":{"desc":"Có bằng thạc sĩ chuyên ngành bất kỳ","score":115.0},"I3":{"desc":"Có bằng thạc sĩ (các) chuyên ngành cụ thể","score":132.0},"J":{"desc":"Đào tạo sau cao học, có bằng Tiến sĩ và có kiến thức vô cùng chuyên sâu.","score":152.0}},"Kinh nghiệm":{"A":{"desc":"Các công việc cơ bản không đòi hỏi kinh nghiệm làm việc trước đây. Có thể đào tạo để thực hiện công việc trong một vài giờ.","score":12.0},"B":{"desc":"Các công việc đơn giản, có thể học trong vòng một tháng. Trong quá trình làm việc được hướng dẫn bằng lời nói và có thể có các quy trình chi tiết bằng văn bản.  \n(không cần kinh nghiệm, công việc có thể thành thạo sau 1 tháng)","score":16.0},"C":{"desc":"Quen thuộc với các công việc không phức tạp, đã được chuẩn hóa, với yêu cầu sử dụng thiết bị và máy móc đơn giản. (3 tháng kinh nghiệm)","score":22.0},"D":{"desc":"Công việc có tính chất thường lệ, nhưng cần có kinh nghiệm giải quyết các trường hợp ngoại lệ và tình huống đặc biệt. (6 tháng kinh nghiệm)","score":29.0},"E":{"desc":"Có kinh nghiệm thực hành thành thạo về một kỹ năng, có thể liên quan đến các hoạt động hoặc thiết bị cụ thể, hoặc các hoạt động tổng hợp yêu cầu tối thiểu 12 tháng kinh nghiệm tương đương. (12 tháng kinh nghiệm)","score":38.0},"F":{"desc":"Có kinh nghiệm liên quan trong một lĩnh vực cụ thể, thường yêu cầu đào tạo chuyên ngành và có sự khéo léo/khả năng làm chủ công việc cao. (1 - 2 năm kinh nghiệm)","score":50.0},"G1":{"desc":"Tối thiểu 3 năm kinh nghiệm chuyên môn, không có kinh nghiệm giám sát nhóm","score":57.0},"G2":{"desc":"Tối thiểu 5 năm kinh nghiệm chuyên môn HOẶC 1 năm kinh nghiệm giám sát nhóm","score":66.0},"G3":{"desc":"Tối thiểu 2-3 năm kinh nghiệm giám sát nhóm","score":76.0},"H1":{"desc":"Tối thiểu 6 năm kinh nghiệm chuyên môn","score":76.0},"H2":{"desc":"Tối thiểu 8 năm kinh nghiệm chuyên môn VÀ/HOẶC 1 năm kinh nghiệm quản lý cấp phòng","score":87.0},"H3":{"desc":"Tối thiểu 2-3 năm kinh nghiệm quản lý cấp phòng","score":100.0},"I1":{"desc":"Tối thiểu 10 năm kinh nghiệm trong lĩnh vực chuyên môn","score":100.0},"I2":{"desc":"Có kinh nghiệm quản lý đồng thời nhiều phòng ban","score":115.0},"I3":{"desc":"Kinh nghiệm tương đương ở cấp điều hành mảng chức năng chủ chốt của tổ chức (giám đốc khối/ phó Tổng giám đốc)","score":132.0},"J":{"desc":"Tổng giám đốc của một tổ chức nhỏ/vừa hoạt động tập trung trong một lĩnh vực.","score":152.0},"K":{"desc":"Tổng giám đốc của một tổ chức lớn hoạt động trong nhiều lĩnh vực, hoặc hoạt động trong một lĩnh vực ở nhiều hơn một quốc gia.","score":200.0},"L":{"desc":"Tổng giám đốc của một tổ chức lớn hoạt động trong nhiều lĩnh vực, ở nhiều quốc gia trên thế giới.","score":264.0}},"Mức độ phức tạp của công việc":{"A1":{"desc":"Những công việc đơn giản, lặp đi lặp lại, đã được mô tả cụ thể, dễ học và không đòi hỏi suy nghĩ độc lập hoặc đưa ra quyết định quan trọng.","multiplier":0.0},"A2":{"desc":"Những công việc đơn giản, lặp đi lặp lại, đã được mô tả cụ thể, dễ học và không đòi hỏi suy nghĩ độc lập hoặc đưa ra quyết định quan trọng.","multiplier":0.05},"A3":{"desc":"Những công việc đơn giản, lặp đi lặp lại, đã được mô tả cụ thể, dễ học và không đòi hỏi suy nghĩ độc lập hoặc đưa ra quyết định quan trọng.","multiplier":0.1},"B1":{"desc":"Ứng dụng các kiến thức và kỹ năng đã có để thực hiện công việc, công việc cụ thể, rõ ràng, không cần đưa ra nhiều quyết định cá nhân.","multiplier":0.15},"B2":{"desc":"Ứng dụng các kiến thức và kỹ năng đã có để thực hiện công việc, công việc cụ thể, rõ ràng, không cần đưa ra nhiều quyết định cá nhân.","multiplier":0.2},"B3":{"desc":"Ứng dụng các kiến thức và kỹ năng đã có để thực hiện công việc, công việc cụ thể, rõ ràng, không cần đưa ra nhiều quyết định cá nhân.","multiplier":0.25},"C1":{"desc":"Công việc có yêu cầu rõ ràng về kết quả cần đạt, cũng như đã có chính sách và thủ tục quy định chi tiết, tuy nhiên thỉnh thoảng cần đưa ra ý kiến độc lập.","multiplier":0.3},"C2":{"desc":"Công việc có yêu cầu rõ ràng về kết quả cần đạt, cũng như đã có chính sách và thủ tục quy định chi tiết, tuy nhiên thỉnh thoảng cần đưa ra ý kiến độc lập.","multiplier":0.35},"C3":{"desc":"Công việc có yêu cầu rõ ràng về kết quả cần đạt, cũng như đã có chính sách và thủ tục quy định chi tiết, tuy nhiên thỉnh thoảng cần đưa ra ý kiến độc lập.","multiplier":0.4},"D1":{"desc":"Công việc có yêu cầu tương đối rõ ràng về kết quả cần đạt, nhưng chưa có cách thức thực hiện. Cần liên tục dung hòa các yêu cầu khác nhau từ các bên liên quan, cũng như giải quyết nhiều tình huống đa dạng, khó đoán trước.","multiplier":0.45},"D2":{"desc":"Công việc có yêu cầu tương đối rõ ràng về kết quả cần đạt, nhưng chưa có cách thức thực hiện. Cần liên tục dung hòa các yêu cầu khác nhau từ các bên liên quan, cũng như giải quyết nhiều tình huống đa dạng, khó đoán trước.","multiplier":0.5},"D3":{"desc":"Công việc có yêu cầu tương đối rõ ràng về kết quả cần đạt, nhưng chưa có cách thức thực hiện. Cần liên tục dung hòa các yêu cầu khác nhau từ các bên liên quan, cũng như giải quyết nhiều tình huống đa dạng, khó đoán trước.","multiplier":0.55},"E1":{"desc":"Công việc yêu cầu cao về khả năng sáng tạo và thích nghi nhằm phản ứng nhanh với sự thay đổi liên tục. Công việc cần kiểm soát, kết nối và thúc đẩy mảng chức năng hoặc các chức năng có tính liên kết trong tổ chức.","multiplier":0.6},"E2":{"desc":"Công việc yêu cầu cao về khả năng sáng tạo và thích nghi nhằm phản ứng nhanh với sự thay đổi liên tục. Công việc cần kiểm soát, kết nối và thúc đẩy mảng chức năng hoặc các chức năng có tính liên kết trong tổ chức.","multiplier":0.65},"E3":{"desc":"Công việc yêu cầu cao về khả năng sáng tạo và thích nghi nhằm phản ứng nhanh với sự thay đổi liên tục. Công việc cần kiểm soát, kết nối và thúc đẩy mảng chức năng hoặc các chức năng có tính liên kết trong tổ chức.","multiplier":0.7},"F1":{"desc":"Điều phối và quản lý nhiều chức năng chuyên môn hóa cao, hoạt động của các chức năng này có thể ảnh hưởng đáng kể đến sự tồn tại của tổ chức trong tương lai dài.","multiplier":0.75},"F2":{"desc":"Điều phối và quản lý nhiều chức năng chuyên môn hóa cao, hoạt động của các chức năng này có thể ảnh hưởng đáng kể đến sự tồn tại của tổ chức trong tương lai dài.","multiplier":0.8},"F3":{"desc":"Điều phối và quản lý nhiều chức năng chuyên môn hóa cao, hoạt động của các chức năng này có thể ảnh hưởng đáng kể đến sự tồn tại của tổ chức trong tương lai dài.","multiplier":0.85}},"Phạm vi công việc":{"A":{"desc":"Thực hiện các công việc, nhiệm vụ cụ thể, không cần giám sát hay liên hệ chặt chẽ với những bộ phận, cá nhân khác. (không giám sát, không phối hợp với cá nhân khác)","multiplier":0.05},"B":{"desc":"Không cần giám sát, nhưng cần liên hệ chặt chẽ với các bộ phận, cá nhân khác để hoàn thành được phạm vi công việc của mình. (không giám sát, có phối hợp với đơn vị cá nhân khác)","multiplier":0.1},"C":{"desc":"Công việc yêu cầu giám sát các cá nhân khác nhằm đạt được những mục tiêu cụ thể, có thể cần cộng tác, phối hợp với các bộ phận khác trong các hoạt động cụ thể. (Trưởng nhóm)","multiplier":0.15},"D":{"desc":"Quản lý một phần hoạt động của một chức năng trong tổ chức. Yêu cầu tham gia lập kế hoạch, chỉ đạo và kiểm soát một số hoạt động trong tổ chức. (Trưởng phòng)D","multiplier":0.2},"E":{"desc":"Quản lý toàn bộ một mảng chức năng trong tổ chức, trong đó bao gồm việc lập kế hoạch, chỉ đạo và kiểm soát tất cả các hoạt động của chức năng đó. (Giám đốc ban/ trung tâm)","multiplier":0.25},"F":{"desc":"Phối hợp và quản lý nhiều chức năng có tính liên kết trong một tổ chức. (Giám đốc Khối/ Phó Tổng giám đốc)","multiplier":0.3},"G":{"desc":"Kiểm soát, định hướng hoạt động toàn bộ tổ chức trực thuộc tập đoàn, có thể có ảnh hưởng tới định hướng chiến lược dài hạn của tập đoàn. (Tổng giám đốc - công ty con của tập đoàn)","multiplier":0.35},"H":{"desc":"Tổng giám đốc của một tổ chức lớn, với ảnh hưởng kiểm soát tới tất cả các định hướng chiến lược dài hạn ở tất cả quốc gia. (Tổng giám đốc – công ty mẹ hoặc doanh nghiệp đa quốc gia)","multiplier":0.4}},"Mức độ giải quyết vấn đề":{"A1":{"desc":"Công việc đơn giản, lặp đi lặp lại. Các vấn đề nhỏ và được giải quyết bằng cách lựa chọn đơn giản giữa những điều đã được học, hoặc có quy định và hướng dẫn cụ thể về cách giải quyết vấn đề.","score":19.0},"A2":{"desc":"Công việc đơn giản, lặp đi lặp lại. Các vấn đề nhỏ và được giải quyết bằng cách lựa chọn đơn giản giữa những điều đã được học, hoặc có quy định và hướng dẫn cụ thể về cách giải quyết vấn đề.","score":22.0},"A3":{"desc":"Công việc đơn giản, lặp đi lặp lại. Các vấn đề nhỏ và được giải quyết bằng cách lựa chọn đơn giản giữa những điều đã được học, hoặc có quy định và hướng dẫn cụ thể về cách giải quyết vấn đề.","score":25.0},"B1":{"desc":"Phần lớn công việc có tính thường lệ nhưng các vấn đề thường phức tạp hơn, yêu cầu tham khảo các tiền lệ trước đó và/hoặc diễn giải các hướng dẫn để giải quyết.","score":29.0},"B2":{"desc":"Phần lớn công việc có tính thường lệ nhưng các vấn đề thường phức tạp hơn, yêu cầu tham khảo các tiền lệ trước đó và/hoặc diễn giải các hướng dẫn để giải quyết.","score":33.0},"B3":{"desc":"Phần lớn công việc có tính thường lệ nhưng các vấn đề thường phức tạp hơn, yêu cầu tham khảo các tiền lệ trước đó và/hoặc diễn giải các hướng dẫn để giải quyết.","score":38.0},"C1":{"desc":"Các vấn đề thường đa dạng, yêu cầu nghiên cứu các trường hợp khác nhau hoặc các tình huống mâu thuẫn nhằm đưa ra giải pháp. Cần có sự sáng tạo và khả năng nhận định, đánh giá khi nghiên cứu và phân tích vấn đề.","score":43.0},"C2":{"desc":"Các vấn đề thường đa dạng, yêu cầu nghiên cứu các trường hợp khác nhau hoặc các tình huống mâu thuẫn nhằm đưa ra giải pháp. Cần có sự sáng tạo và khả năng nhận định, đánh giá khi nghiên cứu và phân tích vấn đề.","score":50.0},"C3":{"desc":"Các vấn đề thường đa dạng, yêu cầu nghiên cứu các trường hợp khác nhau hoặc các tình huống mâu thuẫn nhằm đưa ra giải pháp. Cần có sự sáng tạo và khả năng nhận định, đánh giá khi nghiên cứu và phân tích vấn đề.","score":57.0},"D1":{"desc":"Các vấn đề ở phạm vi nhóm hoặc phòng ban, có một vài yếu tố bất thường, có thể chưa từng xảy ra. Cần nghiên cứu và phân tích để đưa ra giải pháp. Các hướng dẫn và chính sách sẵn có chỉ đưa ra một phần cách giải quyết, cần sáng tạo và có khả năng phán đoán để giải quyết vấn đề.","score":66.0},"D2":{"desc":"Các vấn đề ở phạm vi nhóm hoặc phòng ban, có một vài yếu tố bất thường, có thể chưa từng xảy ra. Cần nghiên cứu và phân tích để đưa ra giải pháp. Các hướng dẫn và chính sách sẵn có chỉ đưa ra một phần cách giải quyết, cần sáng tạo và có khả năng phán đoán để giải quyết vấn đề.","score":76.0},"D3":{"desc":"Các vấn đề ở phạm vi nhóm hoặc phòng ban, có một vài yếu tố bất thường, có thể chưa từng xảy ra. Cần nghiên cứu và phân tích để đưa ra giải pháp. Các hướng dẫn và chính sách sẵn có chỉ đưa ra một phần cách giải quyết, cần sáng tạo và có khả năng phán đoán để giải quyết vấn đề.","score":87.0},"E1":{"desc":"Các vấn đề phức tạp ở quy mô một chức năng, cần đánh giá một vài giải pháp khác nhau. Có thể có khung chung hướng dẫn cách giải quyết vấn đề, tuy nhiên đòi hỏi sự sáng tạo và khả năng nhận định, đánh giá để tìm ra giải pháp khả thi nhất.","score":100.0},"E2":{"desc":"Các vấn đề phức tạp ở quy mô một chức năng, cần đánh giá một vài giải pháp khác nhau. Có thể có khung chung hướng dẫn cách giải quyết vấn đề, tuy nhiên đòi hỏi sự sáng tạo và khả năng nhận định, đánh giá để tìm ra giải pháp khả thi nhất.","score":115.0},"E3":{"desc":"Các vấn đề phức tạp ở quy mô một chức năng, cần đánh giá một vài giải pháp khác nhau. Có thể có khung chung hướng dẫn cách giải quyết vấn đề, tuy nhiên đòi hỏi sự sáng tạo và khả năng nhận định, đánh giá để tìm ra giải pháp khả thi nhất.","score":132.0},"F1":{"desc":"Các vấn đề phức tạp, nhiều khía cạnh ở quy mô nhiều chức năng, yêu cầu nghiên cứu sâu về nguyên nhân và mức độ ảnh hưởng. Chính sách công ty có thể hướng dẫn chung về cách giải quyết, nhưng giải pháp đưa ra có thể sẽ làm thay đổi các chính sách hiện hữu","score":152.0},"F2":{"desc":"Các vấn đề phức tạp, nhiều khía cạnh ở quy mô nhiều chức năng, yêu cầu nghiên cứu sâu về nguyên nhân và mức độ ảnh hưởng. Chính sách công ty có thể hướng dẫn chung về cách giải quyết, nhưng giải pháp đưa ra có thể sẽ làm thay đổi các chính sách hiện hữu","score":175.0},"F3":{"desc":"Các vấn đề phức tạp, nhiều khía cạnh ở quy mô nhiều chức năng, yêu cầu nghiên cứu sâu về nguyên nhân và mức độ ảnh hưởng. Chính sách công ty có thể hướng dẫn chung về cách giải quyết, nhưng giải pháp đưa ra có thể sẽ làm thay đổi các chính sách hiện hữu","score":200.0},"G1":{"desc":"Các vấn đề mới lạ, mỗi vấn đề yêu cầu cách tiếp cận hoàn toàn độc lập. Cần ứng dụng những phương pháp nghiên cứu và phân tích phức tạp. Giải pháp tạo ra các chính sách và chiến lược mới cho công ty","score":230.0},"G2":{"desc":"Các vấn đề mới lạ, mỗi vấn đề yêu cầu cách tiếp cận hoàn toàn độc lập. Cần ứng dụng những phương pháp nghiên cứu và phân tích phức tạp. Giải pháp tạo ra các chính sách và chiến lược mới cho công ty","score":264.0},"G3":{"desc":"Các vấn đề mới lạ, mỗi vấn đề yêu cầu cách tiếp cận hoàn toàn độc lập. Cần ứng dụng những phương pháp nghiên cứu và phân tích phức tạp. Giải pháp tạo ra các chính sách và chiến lược mới cho công ty","score":304.0},"H1":{"desc":"Các vấn đề và loại giải pháp đưa ra có thể tạo ảnh hưởng sâu rộng không chỉ với bản thân tổ chức. Giải pháp có thể phát triển những khái niệm và phương pháp tiếp cận mới, đóng góp những phát hiện lớn có tính khoa học, nâng cấp kiến thức và suy nghĩ cho xã hội.","score":350.0},"H2":{"desc":"Các vấn đề và loại giải pháp đưa ra có thể tạo ảnh hưởng sâu rộng không chỉ với bản thân tổ chức. Giải pháp có thể phát triển những khái niệm và phương pháp tiếp cận mới, đóng góp những phát hiện lớn có tính khoa học, nâng cấp kiến thức và suy nghĩ cho xã hội.","score":400.0},"H3":{"desc":"Các vấn đề và loại giải pháp đưa ra có thể tạo ảnh hưởng sâu rộng không chỉ với bản thân tổ chức. Giải pháp có thể phát triển những khái niệm và phương pháp tiếp cận mới, đóng góp những phát hiện lớn có tính khoa học, nâng cấp kiến thức và suy nghĩ cho xã hội.","score":460.0}},"Mức độ cần được chỉ dẫn, giám sát":{"A1":{"desc":"Nhiệm vụ đơn giản, công việc cần giám sát chặt chẽ, tất cả các công việc đều được kiểm tra chi tiết.","score":16.0},"A2":{"desc":"Nhiệm vụ đơn giản, công việc cần giám sát chặt chẽ, tất cả các công việc đều được kiểm tra chi tiết.","score":19.0},"A3":{"desc":"Nhiệm vụ đơn giản, công việc cần giám sát chặt chẽ, tất cả các công việc đều được kiểm tra chi tiết.","score":22.0},"B1":{"desc":"Có chỉ dẫn chi tiết cho các nhiệm vụ nhưng người đảm nhiệm công việc được tự do sắp xếp thứ tự thực hiện nhiệm vụ. Công việc được giám sát chặt chẽ và hầu hết các công việc được kiểm tra.","score":25.0},"B2":{"desc":"Có chỉ dẫn chi tiết cho các nhiệm vụ nhưng người đảm nhiệm công việc được tự do sắp xếp thứ tự thực hiện nhiệm vụ. Công việc được giám sát chặt chẽ và hầu hết các công việc được kiểm tra.","score":29.0},"B3":{"desc":"Có chỉ dẫn chi tiết cho các nhiệm vụ nhưng người đảm nhiệm công việc được tự do sắp xếp thứ tự thực hiện nhiệm vụ. Công việc được giám sát chặt chẽ và hầu hết các công việc được kiểm tra.","score":33.0},"C1":{"desc":"Công việc cá nhân cần tuân thủ các quy định, thủ tục, cũng như cần đạt được các mục tiêu đã đề ra. Công việc được hướng dẫn và hỗ trợ, rà soát định kỳ.","score":38.0},"C2":{"desc":"Công việc cá nhân cần tuân thủ các quy định, thủ tục, cũng như cần đạt được các mục tiêu đã đề ra. Công việc được hướng dẫn và hỗ trợ, rà soát định kỳ.","score":43.0},"C3":{"desc":"Công việc cá nhân cần tuân thủ các quy định, thủ tục, cũng như cần đạt được các mục tiêu đã đề ra. Công việc được hướng dẫn và hỗ trợ, rà soát định kỳ.","score":50.0},"D1":{"desc":"Công việc đã rõ những mục tiêu cần hoàn thành, người đảm nhận công việc được chỉ dẫn chung, không được kiểm tra thường xuyên trong quá trình thực hiện nhiệm vụ, nhưng được quản lý trực tiếp hỗ trợ nếu cần.","score":57.0},"D2":{"desc":"Công việc đã rõ những mục tiêu cần hoàn thành, người đảm nhận công việc được chỉ dẫn chung, không được kiểm tra thường xuyên trong quá trình thực hiện nhiệm vụ, nhưng được quản lý trực tiếp hỗ trợ nếu cần.","score":66.0},"D3":{"desc":"Công việc đã rõ những mục tiêu cần hoàn thành, người đảm nhận công việc được chỉ dẫn chung, không được kiểm tra thường xuyên trong quá trình thực hiện nhiệm vụ, nhưng được quản lý trực tiếp hỗ trợ nếu cần.","score":76.0},"E1":{"desc":"Người đảm nhận công việc cần lên kế hoạch làm việc cho phòng ban để đạt mục tiêu. Việc hướng dẫn, kiểm tra trong quá trình thực hiện rất ít, không chính thức. Người đảm nhiệm công việc cần độc lập làm việc nhưng có thể được hướng dẫn nếu cần.","score":87.0},"E2":{"desc":"Người đảm nhận công việc cần lên kế hoạch làm việc cho phòng ban để đạt mục tiêu. Việc hướng dẫn, kiểm tra trong quá trình thực hiện rất ít, không chính thức. Người đảm nhiệm công việc cần độc lập làm việc nhưng có thể được hướng dẫn nếu cần.","score":100.0},"E3":{"desc":"Người đảm nhận công việc cần lên kế hoạch làm việc cho phòng ban để đạt mục tiêu. Việc hướng dẫn, kiểm tra trong quá trình thực hiện rất ít, không chính thức. Người đảm nhiệm công việc cần độc lập làm việc nhưng có thể được hướng dẫn nếu cần.","score":115.0},"F1":{"desc":"Người đảm nhận công việc được tham gia thảo luận các mục tiêu của mảng  và cần lên kế hoạch làm việc để đạt được các mục tiêu đó.","score":132.0},"F2":{"desc":"Người đảm nhận công việc được tham gia thảo luận các mục tiêu của mảng và cần lên kế hoạch làm việc để đạt được các mục tiêu đó.","score":152.0},"F3":{"desc":"Người đảm nhận công việc được tham gia thảo luận các mục tiêu của mảng  và cần lên kế hoạch làm việc để đạt được các mục tiêu đó.","score":175.0},"G1":{"desc":"Đưa ra mục tiêu cho nhóm các chức năng có tính liên kết để đạt được những mục tiêu, định hướng chung của tổ chức. Công việc thường không có hướng dẫn mà chỉ có ý kiến cố vấn, yêu cầu ra quyết định một cách độc lập.","score":200.0},"G2":{"desc":"Đưa ra mục tiêu cho nhóm các chức năng có tính liên kết để đạt được những mục tiêu, định hướng chung của tổ chức. Công việc thường không có hướng dẫn mà chỉ có ý kiến cố vấn, yêu cầu ra quyết định một cách độc lập.","score":230.0},"G3":{"desc":"Đưa ra mục tiêu cho nhóm các chức năng có tính liên kết để đạt được những mục tiêu, định hướng chung của tổ chức. Công việc thường không có hướng dẫn mà chỉ có ý kiến cố vấn, yêu cầu ra quyết định một cách độc lập.","score":264.0},"H1":{"desc":"Trách nhiệm chỉ giới hạn ở phạm vi các chính sách của công ty do HĐQT quyết định. Tự đưa ra mục tiêu, hành động cho cả tổ chức.","score":304.0},"H2":{"desc":"Trách nhiệm chỉ giới hạn ở phạm vi các chính sách của công ty do HĐQT quyết định. Tự đưa ra mục tiêu, hành động cho cả tổ chức.","score":350.0},"H3":{"desc":"Trách nhiệm chỉ giới hạn ở phạm vi các chính sách của công ty do HĐQT quyết định. Tự đưa ra mục tiêu, hành động cho cả tổ chức.","score":400.0}},"Mức độ liên lạc khi thực hiện công việc":{"A1":{"desc_row":"Liên hệ chỉ cho mục đích xã giao.","desc_col":"Cần liên hệ ngoài tổ chức ở mức tối thiểu","score":14.0},"A2":{"desc_row":"Liên hệ chỉ cho mục đích xã giao.","desc_col":"Đàm phán nhỏ và liên hệ tương đối nhiều để giải quyết những khó khăn và vấn đề thông thường","score":19.0},"A3":{"desc_row":"Liên hệ chỉ cho mục đích xã giao.","desc_col":"Liên hệ tương đối nhiều để quảng bá tổ chức và đạt được những mục tiêu đã định sẵn","score":22.0},"A4":{"desc_row":"Liên hệ chỉ cho mục đích xã giao.","desc_col":"Liên hệ đáng kể về các vấn đề nhạy cảm, đòi hỏi có quan hệ và đàm phán ở cấp cao để giải quyết những khác biệt đang tồn tại","score":25.0},"A5":{"desc_row":"Liên hệ chỉ cho mục đích xã giao.","desc_col":"Những đàm phán then chốt, liên quan đến những vấn đề tối quan trọng đối với tổ chức","score":29.0},"B1":{"desc_row":"Cần thảo luận công việc và trao đổi thông tin với các nhân sự khác trong tổ chức, ví dụ để lấy thông tin đầu vào cho công việc của vị trí.","desc_col":"Cần liên hệ ngoài tổ chức ở mức tối thiểu","score":25.0},"B2":{"desc_row":"Cần thảo luận công việc và trao đổi thông tin với các nhân sự khác trong tổ chức, ví dụ để lấy thông tin đầu vào cho công việc của vị trí.","desc_col":"Đàm phán nhỏ và liên hệ tương đối nhiều để giải quyết những khó khăn và vấn đề thông thường","score":29.0},"B3":{"desc_row":"Cần thảo luận công việc và trao đổi thông tin với các nhân sự khác trong tổ chức, ví dụ để lấy thông tin đầu vào cho công việc của vị trí.","desc_col":"Liên hệ tương đối nhiều để quảng bá tổ chức và đạt được những mục tiêu đã định sẵn","score":33.0},"B4":{"desc_row":"Cần thảo luận công việc và trao đổi thông tin với các nhân sự khác trong tổ chức, ví dụ để lấy thông tin đầu vào cho công việc của vị trí.","desc_col":"Liên hệ đáng kể về các vấn đề nhạy cảm, đòi hỏi có quan hệ và đàm phán ở cấp cao để giải quyết những khác biệt đang tồn tại","score":38.0},"B5":{"desc_row":"Cần thảo luận công việc và trao đổi thông tin với các nhân sự khác trong tổ chức, ví dụ để lấy thông tin đầu vào cho công việc của vị trí.","desc_col":"Những đàm phán then chốt, liên quan đến những vấn đề tối quan trọng đối với tổ chức","score":43.0},"C1":{"desc_row":"Cần cộng tác với các bộ phận khác trong tổ chức để đạt mục đích chung.","desc_col":"Cần liên hệ ngoài tổ chức ở mức tối thiểu","score":38.0},"C2":{"desc_row":"Cần cộng tác với các bộ phận khác trong tổ chức để đạt mục đích chung.","desc_col":"Đàm phán nhỏ và liên hệ tương đối nhiều để giải quyết những khó khăn và vấn đề thông thường","score":43.0},"C3":{"desc_row":"Cần cộng tác với các bộ phận khác trong tổ chức để đạt mục đích chung.","desc_col":"Liên hệ tương đối nhiều để quảng bá tổ chức và đạt được những mục tiêu đã định sẵn","score":50.0},"C4":{"desc_row":"Cần cộng tác với các bộ phận khác trong tổ chức để đạt mục đích chung.","desc_col":"Liên hệ đáng kể về các vấn đề nhạy cảm, đòi hỏi có quan hệ và đàm phán ở cấp cao để giải quyết những khác biệt đang tồn tại","score":57.0},"C5":{"desc_row":"Cần cộng tác với các bộ phận khác trong tổ chức để đạt mục đích chung.","desc_col":"Những đàm phán then chốt, liên quan đến những vấn đề tối quan trọng đối với tổ chức","score":66.0},"D11":{"desc_row":"Giám sát cấp nhóm","desc_col":"Cần liên hệ ngoài tổ chức ở mức tối thiểu","score":50.0},"D12":{"desc_row":"Giám sát cấp nhóm","desc_col":"Đàm phán nhỏ và liên hệ tương đối nhiều để giải quyết những khó khăn và vấn đề thông thường","score":57.0},"D13":{"desc_row":"Giám sát cấp nhóm","desc_col":"Liên hệ tương đối nhiều để quảng bá tổ chức và đạt được những mục tiêu đã định sẵn","score":66.0},"D14":{"desc_row":"Giám sát cấp nhóm","desc_col":"Liên hệ đáng kể về các vấn đề nhạy cảm, đòi hỏi có quan hệ và đàm phán ở cấp cao để giải quyết những khác biệt đang tồn tại","score":76.0},"D15":{"desc_row":"Giám sát cấp nhóm","desc_col":"Những đàm phán then chốt, liên quan đến những vấn đề tối quan trọng đối với tổ chức","score":87.0},"D21":{"desc_row":"Quản lý cấp phòng","desc_col":"Cần liên hệ ngoài tổ chức ở mức tối thiểu","score":57.0},"D22":{"desc_row":"Quản lý cấp phòng","desc_col":"Đàm phán nhỏ và liên hệ tương đối nhiều để giải quyết những khó khăn và vấn đề thông thường","score":66.0},"D23":{"desc_row":"Quản lý cấp phòng","desc_col":"Liên hệ tương đối nhiều để quảng bá tổ chức và đạt được những mục tiêu đã định sẵn","score":76.0},"D24":{"desc_row":"Quản lý cấp phòng","desc_col":"Liên hệ đáng kể về các vấn đề nhạy cảm, đòi hỏi có quan hệ và đàm phán ở cấp cao để giải quyết những khác biệt đang tồn tại","score":87.0},"D25":{"desc_row":"Quản lý cấp phòng","desc_col":"Những đàm phán then chốt, liên quan đến những vấn đề tối quan trọng đối với tổ chức","score":100.0},"D31":{"desc_row":"Quản lý cấp ban/trung tâm","desc_col":"Cần liên hệ ngoài tổ chức ở mức tối thiểu","score":66.0},"D32":{"desc_row":"Quản lý cấp ban/trung tâm","desc_col":"Đàm phán nhỏ và liên hệ tương đối nhiều để giải quyết những khó khăn và vấn đề thông thường","score":76.0},"D33":{"desc_row":"Quản lý cấp ban/trung tâm","desc_col":"Liên hệ tương đối nhiều để quảng bá tổ chức và đạt được những mục tiêu đã định sẵn","score":87.0},"D34":{"desc_row":"Quản lý cấp ban/trung tâm","desc_col":"Liên hệ đáng kể về các vấn đề nhạy cảm, đòi hỏi có quan hệ và đàm phán ở cấp cao để giải quyết những khác biệt đang tồn tại","score":100.0},"D35":{"desc_row":"Quản lý cấp ban/trung tâm","desc_col":"Những đàm phán then chốt, liên quan đến những vấn đề tối quan trọng đối với tổ chức","score":115.0},"E1":{"desc_row":"Liên hệ ở phạm vi rộng với phần lớn các chức năng trong tổ chức, cần lãnh đạo, thúc đẩy và chỉ đạo các nhân viên trong các điều kiện nhạy cảm.","desc_col":"Cần liên hệ ngoài tổ chức ở mức tối thiểu","score":87.0},"E2":{"desc_row":"Liên hệ ở phạm vi rộng với phần lớn các chức năng trong tổ chức, cần lãnh đạo, thúc đẩy và chỉ đạo các nhân viên trong các điều kiện nhạy cảm.","desc_col":"Đàm phán nhỏ và liên hệ tương đối nhiều để giải quyết những khó khăn và vấn đề thông thường","score":100.0},"E3":{"desc_row":"Liên hệ ở phạm vi rộng với phần lớn các chức năng trong tổ chức, cần lãnh đạo, thúc đẩy và chỉ đạo các nhân viên trong các điều kiện nhạy cảm.","desc_col":"Liên hệ tương đối nhiều để quảng bá tổ chức và đạt được những mục tiêu đã định sẵn","score":115.0},"E4":{"desc_row":"Liên hệ ở phạm vi rộng với phần lớn các chức năng trong tổ chức, cần lãnh đạo, thúc đẩy và chỉ đạo các nhân viên trong các điều kiện nhạy cảm.","desc_col":"Liên hệ đáng kể về các vấn đề nhạy cảm, đòi hỏi có quan hệ và đàm phán ở cấp cao để giải quyết những khác biệt đang tồn tại","score":132.0},"E5":{"desc_row":"Liên hệ ở phạm vi rộng với phần lớn các chức năng trong tổ chức, cần lãnh đạo, thúc đẩy và chỉ đạo các nhân viên trong các điều kiện nhạy cảm.","desc_col":"Những đàm phán then chốt, liên quan đến những vấn đề tối quan trọng đối với tổ chức","score":152.0},"F1":{"desc_row":"Phối hợp và chỉ đạo quản lý các cấp trong tất cả các lĩnh vực của tổ chức.","desc_col":"Cần liên hệ ngoài tổ chức ở mức tối thiểu","score":132.0},"F2":{"desc_row":"Phối hợp và chỉ đạo quản lý các cấp trong tất cả các lĩnh vực của tổ chức.","desc_col":"Đàm phán nhỏ và liên hệ tương đối nhiều để giải quyết những khó khăn và vấn đề thông thường","score":152.0},"F3":{"desc_row":"Phối hợp và chỉ đạo quản lý các cấp trong tất cả các lĩnh vực của tổ chức.","desc_col":"Liên hệ tương đối nhiều để quảng bá tổ chức và đạt được những mục tiêu đã định sẵn","score":175.0},"F4":{"desc_row":"Phối hợp và chỉ đạo quản lý các cấp trong tất cả các lĩnh vực của tổ chức.","desc_col":"Liên hệ đáng kể về các vấn đề nhạy cảm, đòi hỏi có quan hệ và đàm phán ở cấp cao để giải quyết những khác biệt đang tồn tại","score":200.0},"F5":{"desc_row":"Phối hợp và chỉ đạo quản lý các cấp trong tất cả các lĩnh vực của tổ chức.","desc_col":"Những đàm phán then chốt, liên quan đến những vấn đề tối quan trọng đối với tổ chức","score":230.0}},"Trách nhiệm giám sát & quản lý":{"A":{"desc_row":"Không quản lý nhân viên","desc_col":"Không áp dụng","score":0.0},"B1":{"desc_row":"Trách nhiệm giám sát ở mức thấp, nhưng hỗ trợ nhân viên mới trong đơn vị (hoặc giám sát/ quản lý 1 nhân viên)","desc_col":"Vị trí công việc giản đơn","score":19.0},"B2":{"desc_row":"Trách nhiệm giám sát ở mức thấp, nhưng hỗ trợ nhân viên mới trong đơn vị (hoặc giám sát/ quản lý 1 nhân viên)","desc_col":"Vị trí chuyên môn","score":22.0},"B3":{"desc_row":"Trách nhiệm giám sát ở mức thấp, nhưng hỗ trợ nhân viên mới trong đơn vị (hoặc giám sát/ quản lý 1 nhân viên)","desc_col":"Vị trí quản lý","score":29.0},"C11":{"desc_row":"Giám sát/quản lý 2 - 4 nhân sự","desc_col":"Vị trí công việc giản đơn","score":25.0},"C12":{"desc_row":"Giám sát/quản lý 2 - 4 nhân sự","desc_col":"Vị trí chuyên môn","score":29.0},"C13":{"desc_row":"Giám sát/quản lý 2 - 4 nhân sự","desc_col":"Vị trí quản lý","score":33.0},"C21":{"desc_row":"Giám sát/quản lý 5 – 7 nhân sự","desc_col":"Vị trí công việc giản đơn","score":29.0},"C22":{"desc_row":"Giám sát/quản lý 5 – 7 nhân sự","desc_col":"Vị trí chuyên môn","score":33.0},"C23":{"desc_row":"Giám sát/quản lý 5 – 7 nhân sự","desc_col":"Vị trí quản lý","score":38.0},"C31":{"desc_row":"Giám sát/quản lý 8 – 10 nhân sự","desc_col":"Vị trí công việc giản đơn","score":33.0},"C32":{"desc_row":"Giám sát/quản lý 8 – 10 nhân sự","desc_col":"Vị trí chuyên môn","score":38.0},"C33":{"desc_row":"Giám sát/quản lý 8 – 10 nhân sự","desc_col":"Vị trí quản lý","score":43.0},"D11":{"desc_row":"Giám sát/quản lý 11 - 16 nhân sự","desc_col":"Vị trí công việc giản đơn","score":38.0},"D12":{"desc_row":"Giám sát/quản lý 11 - 16 nhân sự","desc_col":"Vị trí chuyên môn","score":43.0},"D13":{"desc_row":"Giám sát/quản lý 11 - 16 nhân sự","desc_col":"Vị trí quản lý","score":50.0},"D21":{"desc_row":"Giám sát/quản lý 17 - 24 nhân sự","desc_col":"Vị trí công việc giản đơn","score":43.0},"D22":{"desc_row":"Giám sát/quản lý 17 - 24 nhân sự","desc_col":"Vị trí chuyên môn","score":50.0},"D23":{"desc_row":"Giám sát/quản lý 17 - 24 nhân sự","desc_col":"Vị trí quản lý","score":57.0},"D31":{"desc_row":"Giám sát/quản lý 25 - 30 nhân sự","desc_col":"Vị trí công việc giản đơn","score":50.0},"D32":{"desc_row":"Giám sát/quản lý 25 - 30 nhân sự","desc_col":"Vị trí chuyên môn","score":57.0},"D33":{"desc_row":"Giám sát/quản lý 25 - 30 nhân sự","desc_col":"Vị trí quản lý","score":66.0},"E11":{"desc_row":"Giám sát/quản lý 31 - 53 nhân sự","desc_col":"Vị trí công việc giản đơn","score":57.0},"E12":{"desc_row":"Giám sát/quản lý 31 - 53 nhân sự","desc_col":"Vị trí chuyên môn","score":66.0},"E13":{"desc_row":"Giám sát/quản lý 31 - 53 nhân sự","desc_col":"Vị trí quản lý","score":76.0},"E21":{"desc_row":"Giám sát/quản lý 54 - 77 nhân sự","desc_col":"Vị trí công việc giản đơn","score":66.0},"E22":{"desc_row":"Giám sát/quản lý 54 - 77 nhân sự","desc_col":"Vị trí chuyên môn","score":76.0},"E23":{"desc_row":"Giám sát/quản lý 54 - 77 nhân sự","desc_col":"Vị trí quản lý","score":87.0},"E31":{"desc_row":"Giám sát/quản lý 78 - 100 nhân sự","desc_col":"Vị trí công việc giản đơn","score":76.0},"E32":{"desc_row":"Giám sát/quản lý 78 - 100 nhân sự","desc_col":"Vị trí chuyên môn","score":87.0},"E33":{"desc_row":"Giám sát/quản lý 78 - 100 nhân sự","desc_col":"Vị trí quản lý","score":100.0},"F11":{"desc_row":"Giám sát/quản lý 101 - 233 nhân sự","desc_col":"Vị trí công việc giản đơn","score":87.0},"F12":{"desc_row":"Giám sát/quản lý 101 - 233 nhân sự","desc_col":"Vị trí chuyên môn","score":100.0},"F13":{"desc_row":"Giám sát/quản lý 101 - 233 nhân sự","desc_col":"Vị trí quản lý","score":115.0},"F21":{"desc_row":"Giám sát/quản lý 234 - 367 nhân sự","desc_col":"Vị trí công việc giản đơn","score":100.0},"F22":{"desc_row":"Giám sát/quản lý 234 - 367 nhân sự","desc_col":"Vị trí chuyên môn","score":115.0},"F23":{"desc_row":"Giám sát/quản lý 234 - 367 nhân sự","desc_col":"Vị trí quản lý","score":132.0},"F31":{"desc_row":"Giám sát/quản lý 368 - 500 nhân sự","desc_col":"Vị trí công việc giản đơn","score":115.0},"F32":{"desc_row":"Giám sát/quản lý 368 - 500 nhân sự","desc_col":"Vị trí chuyên môn","score":132.0},"F33":{"desc_row":"Giám sát/quản lý 368 - 500 nhân sự","desc_col":"Vị trí quản lý","score":152.0},"G11":{"desc_row":"Giám sát/quản lý 501 - 1000 nhân sự","desc_col":"Vị trí công việc giản đơn","score":132.0},"G12":{"desc_row":"Giám sát/quản lý 501 - 1000 nhân sự","desc_col":"Vị trí chuyên môn","score":152.0},"G13":{"desc_row":"Giám sát/quản lý 501 - 1000 nhân sự","desc_col":"Vị trí quản lý","score":175.0},"G21":{"desc_row":"Giám sát/quản lý 1001 - 1500 nhân sự","desc_col":"Vị trí công việc giản đơn","score":152.0},"G22":{"desc_row":"Giám sát/quản lý 1001 - 1500 nhân sự","desc_col":"Vị trí chuyên môn","score":175.0},"G23":{"desc_row":"Giám sát/quản lý 1001 - 1500 nhân sự","desc_col":"Vị trí quản lý","score":200.0},"G31":{"desc_row":"Giám sát/quản lý 1501 - 2000 nhân sự","desc_col":"Vị trí công việc giản đơn","score":175.0},"G32":{"desc_row":"Giám sát/quản lý 1501 - 2000 nhân sự","desc_col":"Vị trí chuyên môn","score":200.0},"G33":{"desc_row":"Giám sát/quản lý 1501 - 2000 nhân sự","desc_col":"Vị trí quản lý","score":230.0},"H11":{"desc_row":"Giám sát/quản lý 2.000 – 5.000 nhân sự","desc_col":"Vị trí công việc giản đơn","score":200.0},"H12":{"desc_row":"Giám sát/quản lý 2.000 – 5.000 nhân sự","desc_col":"Vị trí chuyên môn","score":230.0},"H13":{"desc_row":"Giám sát/quản lý 2.000 – 5.000 nhân sự","desc_col":"Vị trí quản lý","score":264.0},"H21":{"desc_row":"Giám sát/quản lý 5.000 – 10.000 nhân sự","desc_col":"Vị trí công việc giản đơn","score":230.0},"H22":{"desc_row":"Giám sát/quản lý 5.000 – 10.000 nhân sự","desc_col":"Vị trí chuyên môn","score":264.0},"H23":{"desc_row":"Giám sát/quản lý 5.000 – 10.000 nhân sự","desc_col":"Vị trí quản lý","score":304.0},"H31":{"desc_row":"Giám sát/quản lý trên 10.000 nhân sự","desc_col":"Vị trí công việc giản đơn","score":264.0},"H32":{"desc_row":"Giám sát/quản lý trên 10.000 nhân sự","desc_col":"Vị trí chuyên môn","score":304.0},"H33":{"desc_row":"Giám sát/quản lý trên 10.000 nhân sự","desc_col":"Vị trí quản lý","score":350.0}},"Tầm ảnh hưởng của các quyết định":{"A1":{"desc_row":"Các quyết định không gây ra thiệt hại nào hoặc công việc có thể làm lại với nguồn lực không đáng kể","desc_col":"Ảnh hưởng đối với cá nhân, nhóm, phòng của tổ chức","score":25.0},"B1":{"desc_row":"Các quyết định có nguy cơ gây ra lãng phí ở mức thấp (dưới 2 triệu VND) hoặc công việc không hiệu quả","desc_col":"Ảnh hưởng đối với cá nhân, nhóm, phòng của tổ chức","score":43.0},"B2":{"desc_row":"Các quyết định có nguy cơ gây ra lãng phí ở mức thấp (dưới 2 triệu VND) hoặc công việc không hiệu quả","desc_col":"Ảnh hưởng đối với ban, trung tâm, khối trong tổ chức","score":57.0},"B3":{"desc_row":"Các quyết định có nguy cơ gây ra lãng phí ở mức thấp (dưới 2 triệu VND) hoặc công việc không hiệu quả","desc_col":"Ảnh hưởng lớn tới toàn tổ chức","score":76.0},"C1":{"desc_row":"Các quyết định có nguy cơ gây ra tổn thất tài chính nhỏ (dưới 50 triệu VND)","desc_col":"Ảnh hưởng đối với cá nhân, nhóm, phòng của tổ chức","score":66.0},"C2":{"desc_row":"Các quyết định có nguy cơ gây ra tổn thất tài chính nhỏ (dưới 50 triệu VND)","desc_col":"Ảnh hưởng đối với ban, trung tâm, khối trong tổ chức","score":87.0},"C3":{"desc_row":"Các quyết định có nguy cơ gây ra tổn thất tài chính nhỏ (dưới 50 triệu VND)","desc_col":"Ảnh hưởng lớn tới toàn tổ chức","score":115.0},"D1":{"desc_row":"Các quyết định có nguy cơ gây ra tổn thất tài chính lớn (trên 50 triệu VND)","desc_col":"Ảnh hưởng đối với cá nhân, nhóm, phòng của tổ chức","score":100.0},"D2":{"desc_row":"Các quyết định có nguy cơ gây ra tổn thất tài chính lớn (trên 50 triệu VND)","desc_col":"Ảnh hưởng đối với ban, trung tâm, khối trong tổ chức","score":132.0},"D3":{"desc_row":"Các quyết định có nguy cơ gây ra tổn thất tài chính lớn (trên 50 triệu VND)","desc_col":"Ảnh hưởng lớn tới toàn tổ chức","score":175.0},"E1":{"desc_row":"Các quyết định ở tầm doanh nghiệp có nguy cơ gây ra thiệt hại nghiêm trọng, ảnh hưởng tới vị thế của tổ chức trên thị trường, khả năng sinh lời và lợi nhuận tiềm năng của tổ chức","desc_col":"Ảnh hưởng đối với cá nhân, nhóm, phòng của tổ chức","score":152.0},"E2":{"desc_row":"Các quyết định ở tầm doanh nghiệp có nguy cơ gây ra thiệt hại nghiêm trọng, ảnh hưởng tới vị thế của tổ chức trên thị trường, khả năng sinh lời và lợi nhuận tiềm năng của tổ chức","desc_col":"Ảnh hưởng đối với ban, trung tâm, khối trong tổ chức","score":200.0},"E3":{"desc_row":"Các quyết định ở tầm doanh nghiệp có nguy cơ gây ra thiệt hại nghiêm trọng, ảnh hưởng tới vị thế của tổ chức trên thị trường, khả năng sinh lời và lợi nhuận tiềm năng của tổ chức","desc_col":"Ảnh hưởng lớn tới toàn tổ chức","score":264.0},"F1":{"desc_row":"Các quyết định có thể trực tiếp đưa đến phá sản và ngừng kinh doanh","desc_col":"Ảnh hưởng đối với cá nhân, nhóm, phòng của tổ chức","score":230.0},"F2":{"desc_row":"Các quyết định có thể trực tiếp đưa đến phá sản và ngừng kinh doanh","desc_col":"Ảnh hưởng đối với ban, trung tâm, khối trong tổ chức","score":304.0},"F3":{"desc_row":"Các quyết định có thể trực tiếp đưa đến phá sản và ngừng kinh doanh","desc_col":"Ảnh hưởng lớn tới toàn tổ chức","score":400.0},"NA":{"desc_row":"Không áp dụng","desc_col":"Không áp dụng","score":0.0}},"Quyền hạn":{"A0":{"desc_row":"Không được phân quyền phê duyệt về mặt tài chính (không có quyền phê duyệt tài chính)","desc_col":"Không được tuyển NV","score":0.0},"A1":{"desc_row":"Không được phân quyền phê duyệt về mặt tài chính (không có quyền phê duyệt tài chính)","desc_col":"Tuyển nhân viên làm việc độc lập","score":12.0},"A2":{"desc_row":"Không được phân quyền phê duyệt về mặt tài chính (không có quyền phê duyệt tài chính)","desc_col":"Tuyển cấp quản lý","score":16.0},"A3":{"desc_row":"Không được phân quyền phê duyệt về mặt tài chính (không có quyền phê duyệt tài chính)","desc_col":"Tuyển cấp lãnh đạo hoặc ngoài kế hoạch","score":22.0},"B0":{"desc_row":"Được duyệt một phần ngân sách\nĐịnh nghĩa một phần: tỉ lệ nhất định của ngân sách được duyệt","desc_col":"Không được tuyển NV","score":12.0},"B1":{"desc_row":"Được duyệt một phần ngân sách\nĐịnh nghĩa một phần: tỉ lệ nhất định của ngân sách được duyệt","desc_col":"Tuyển nhân viên làm việc độc lập","score":19.0},"B2":{"desc_row":"Được duyệt một phần ngân sách\nĐịnh nghĩa một phần: tỉ lệ nhất định của ngân sách được duyệt","desc_col":"Tuyển cấp quản lý","score":25.0},"B3":{"desc_row":"Được duyệt một phần ngân sách\nĐịnh nghĩa một phần: tỉ lệ nhất định của ngân sách được duyệt","desc_col":"Tuyển cấp lãnh đạo hoặc ngoài kế hoạch","score":33.0},"C0":{"desc_row":"Được duyệt toàn bộ ngân sách","desc_col":"Không được tuyển NV","score":19.0},"C1":{"desc_row":"Được duyệt toàn bộ ngân sách","desc_col":"Tuyển nhân viên làm việc độc lập","score":29.0},"C2":{"desc_row":"Được duyệt toàn bộ ngân sách","desc_col":"Tuyển cấp quản lý","score":38.0},"C3":{"desc_row":"Được duyệt toàn bộ ngân sách","desc_col":"Tuyển cấp lãnh đạo hoặc ngoài kế hoạch","score":50.0},"D0":{"desc_row":"Được duyệt ngoài ngân sách dưới hoặc bằng 5% ngân sách lũy kế được duyệt","desc_col":"Không được tuyển NV","score":29.0},"D1":{"desc_row":"Được duyệt ngoài ngân sách dưới hoặc bằng 5% ngân sách lũy kế được duyệt","desc_col":"Tuyển nhân viên làm việc độc lập","score":43.0},"D2":{"desc_row":"Được duyệt ngoài ngân sách dưới hoặc bằng 5% ngân sách lũy kế được duyệt","desc_col":"Tuyển cấp quản lý","score":57.0},"D3":{"desc_row":"Được duyệt ngoài ngân sách dưới hoặc bằng 5% ngân sách lũy kế được duyệt","desc_col":"Tuyển cấp lãnh đạo hoặc ngoài kế hoạch","score":76.0},"E0":{"desc_row":"Được duyệt ngoài ngân sách trên 5% ngân sách lũy kế được duyệt","desc_col":"Không được tuyển NV","score":43.0},"E1":{"desc_row":"Được duyệt ngoài ngân sách trên 5% ngân sách lũy kế được duyệt","desc_col":"Tuyển nhân viên làm việc độc lập","score":66.0},"E2":{"desc_row":"Được duyệt ngoài ngân sách trên 5% ngân sách lũy kế được duyệt","desc_col":"Tuyển cấp quản lý","score":87.0},"E3":{"desc_row":"Được duyệt ngoài ngân sách trên 5% ngân sách lũy kế được duyệt","desc_col":"Tuyển cấp lãnh đạo hoặc ngoài kế hoạch","score":115.0},"NA":{"desc_row":"Không áp dụng","desc_col":"Không áp dụng","score":0.0}},"Môi trường làm việc":{"A1":{"desc_row":"Công việc thực hiện trong nhà trong điều kiện văn phòng hầu như không bị ảnh hưởng bởi môi trường bên ngoài","desc_col":"Rất ít có khả năng có chấn thương thân thể","score":12.0},"A2":{"desc_row":"Công việc thực hiện trong nhà trong điều kiện văn phòng hầu như không bị ảnh hưởng bởi môi trường bên ngoài","desc_col":"Thường xuyên có khả năng xảy ra chấn thương thân thể như bị cắt, thâm tím","score":16.0},"A3":{"desc_row":"Công việc thực hiện trong nhà trong điều kiện văn phòng hầu như không bị ảnh hưởng bởi môi trường bên ngoài","desc_col":"Liên tục có khả năng xảy ra chấn thương thân thể nghiêm trọng","score":22.0},"B1":{"desc_row":"Công việc thường được thực hiện trong nhà trong điều kiện làm việc dễ chịu, đôi khi có những ảnh hưởng khó chịu của môi trường như tiếng ồn, nhiệt độ và chất bẩn","desc_col":"Rất ít có khả năng có chấn thương thân thể","score":19.0},"B2":{"desc_row":"Công việc thường được thực hiện trong nhà trong điều kiện làm việc dễ chịu, đôi khi có những ảnh hưởng khó chịu của môi trường như tiếng ồn, nhiệt độ và chất bẩn","desc_col":"Thường xuyên có khả năng xảy ra chấn thương thân thể như bị cắt, thâm tím","score":25.0},"B3":{"desc_row":"Công việc thường được thực hiện trong nhà trong điều kiện làm việc dễ chịu, đôi khi có những ảnh hưởng khó chịu của môi trường như tiếng ồn, nhiệt độ và chất bẩn","desc_col":"Liên tục có khả năng xảy ra chấn thương thân thể nghiêm trọng","score":33.0},"C1":{"desc_row":"Công việc trong nhà với những ảnh hưởng khó chịu của môi trường như tiếng ồn, nhiệt độ và chất bẩn","desc_col":"Rất ít có khả năng có chấn thương thân thể","score":29.0},"C2":{"desc_row":"Công việc trong nhà với những ảnh hưởng khó chịu của môi trường như tiếng ồn, nhiệt độ và chất bẩn","desc_col":"Thường xuyên có khả năng xảy ra chấn thương thân thể như bị cắt, thâm tím","score":38.0},"C3":{"desc_row":"Công việc trong nhà với những ảnh hưởng khó chịu của môi trường như tiếng ồn, nhiệt độ và chất bẩn","desc_col":"Liên tục có khả năng xảy ra chấn thương thân thể nghiêm trọng","score":50.0},"D1":{"desc_row":"Phần lớn công việc thực hiện ngoài trời nhưng không yêu cầu phải duy trì công việc trong điều kiện thời tiết khắc nghiệt","desc_col":"Rất ít có khả năng có chấn thương thân thể","score":43.0},"D2":{"desc_row":"Phần lớn công việc thực hiện ngoài trời nhưng không yêu cầu phải duy trì công việc trong điều kiện thời tiết khắc nghiệt","desc_col":"Thường xuyên có khả năng xảy ra chấn thương thân thể như bị cắt, thâm tím","score":57.0},"D3":{"desc_row":"Phần lớn công việc thực hiện ngoài trời nhưng không yêu cầu phải duy trì công việc trong điều kiện thời tiết khắc nghiệt","desc_col":"Liên tục có khả năng xảy ra chấn thương thân thể nghiêm trọng","score":76.0},"E1":{"desc_row":"Công việc hầu hết thực hiện ngoài trời. Liên tục chịu ảnh hưởng của nhiều loại hình khí hậu và những ảnh hưởng môi trường khó chịu","desc_col":"Rất ít có khả năng có chấn thương thân thể","score":66.0},"E2":{"desc_row":"Công việc hầu hết thực hiện ngoài trời. Liên tục chịu ảnh hưởng của nhiều loại hình khí hậu và những ảnh hưởng môi trường khó chịu","desc_col":"Thường xuyên có khả năng xảy ra chấn thương thân thể như bị cắt, thâm tím","score":87.0},"E3":{"desc_row":"Công việc hầu hết thực hiện ngoài trời. Liên tục chịu ảnh hưởng của nhiều loại hình khí hậu và những ảnh hưởng môi trường khó chịu","desc_col":"Liên tục có khả năng xảy ra chấn thương thân thể nghiêm trọng","score":115.0},"NA":{"desc_row":"Không áp dụng","desc_col":"Không áp dụng","score":0.0}},"Yêu cầu thể lực đối với công việc":{"A1":{"desc_row":"Công việc thường được thực hiện ở tư thế ngồi, đôi khi được đứng và đi lại tự do","desc_col":"Không yêu cầu hoặc có yêu cầu nâng hàng nhẹ","score":22.0},"A2":{"desc_row":"Công việc thường được thực hiện ở tư thế ngồi, đôi khi được đứng và đi lại tự do","desc_col":"Nâng nhẹ và/hoặc thi thoảng nâng hàng ở mức vừa","score":25.299999999999997},"A3":{"desc_row":"Công việc thường được thực hiện ở tư thế ngồi, đôi khi được đứng và đi lại tự do","desc_col":"Thường xuyên nâng hàng ở mức vừa và đôi khi nâng hàng nặng","score":33.0},"A4":{"desc_row":"Công việc thường được thực hiện ở tư thế ngồi, đôi khi được đứng và đi lại tự do","desc_col":"Thường xuyên nâng hàng nặng","score":43.0},"B1":{"desc_row":"Phần lớn công việc thực hiện ở tư thế đứng và/hoặc đi lại, đôi khi ở tư thế ngồi","desc_col":"Không yêu cầu hoặc có yêu cầu nâng hàng nhẹ","score":29.0},"B2":{"desc_row":"Phần lớn công việc thực hiện ở tư thế đứng và/hoặc đi lại, đôi khi ở tư thế ngồi","desc_col":"Nâng nhẹ và/hoặc thi thoảng nâng hàng ở mức vừa","score":33.0},"B3":{"desc_row":"Phần lớn công việc thực hiện ở tư thế đứng và/hoặc đi lại, đôi khi ở tư thế ngồi","desc_col":"Thường xuyên nâng hàng ở mức vừa và đôi khi nâng hàng nặng","score":43.0},"B4":{"desc_row":"Phần lớn công việc thực hiện ở tư thế đứng và/hoặc đi lại, đôi khi ở tư thế ngồi","desc_col":"Thường xuyên nâng hàng nặng","score":57.0},"C1":{"desc_row":"Công việc có những giai đoạn ngắn cần cúi gập, uốn người, quỳ hoặc trèo","desc_col":"Không yêu cầu hoặc có yêu cầu nâng hàng nhẹ","score":38.0},"C2":{"desc_row":"Công việc có những giai đoạn ngắn cần cúi gập, uốn người, quỳ hoặc trèo","desc_col":"Nâng nhẹ và/hoặc thi thoảng nâng hàng ở mức vừa","score":43.0},"C3":{"desc_row":"Công việc có những giai đoạn ngắn cần cúi gập, uốn người, quỳ hoặc trèo","desc_col":"Thường xuyên nâng hàng ở mức vừa và đôi khi nâng hàng nặng","score":57.0},"C4":{"desc_row":"Công việc có những giai đoạn ngắn cần cúi gập, uốn người, quỳ hoặc trèo","desc_col":"Thường xuyên nâng hàng nặng","score":76.0},"D1":{"desc_row":"Công việc thường xuyên phải cúi gập, uốn người, quỳ hoặc trèo","desc_col":"Không yêu cầu hoặc có yêu cầu nâng hàng nhẹ","score":50.0},"D2":{"desc_row":"Công việc thường xuyên phải cúi gập, uốn người, quỳ hoặc trèo","desc_col":"Nâng nhẹ và/hoặc thi thoảng nâng hàng ở mức vừa","score":57.0},"D3":{"desc_row":"Công việc thường xuyên phải cúi gập, uốn người, quỳ hoặc trèo","desc_col":"Thường xuyên nâng hàng ở mức vừa và đôi khi nâng hàng nặng","score":76.0},"D4":{"desc_row":"Công việc thường xuyên phải cúi gập, uốn người, quỳ hoặc trèo","desc_col":"Thường xuyên nâng hàng nặng","score":100.0},"NA":{"desc_row":"Không áp dụng","desc_col":"Không áp dụng","score":0.0}}}

# Grades đúng theo từng tiêu chí (từ file Excel)
FACTOR_GRADES = {"Trình độ học vấn":["A","B","C","D","E","F1","F2","G1","G2","H1","H2","I1","I2","I3","J"],"Kinh nghiệm":["A","B","C","D","E","F","G1","G2","G3","H1","H2","H3","I1","I2","I3","J","K","L"],"Mức độ phức tạp của công việc":["A1","A2","A3","B1","B2","B3","C1","C2","C3","D1","D2","D3","E1","E2","E3","F1","F2","F3"],"Phạm vi công việc":["A","B","C","D","E","F","G","H"],"Mức độ giải quyết vấn đề":["A1","A2","A3","B1","B2","B3","C1","C2","C3","D1","D2","D3","E1","E2","E3","F1","F2","F3","G1","G2","G3","H1","H2","H3"],"Mức độ cần được chỉ dẫn, giám sát":["A1","A2","A3","B1","B2","B3","C1","C2","C3","D1","D2","D3","E1","E2","E3","F1","F2","F3","G1","G2","G3","H1","H2","H3"],"Mức độ liên lạc khi thực hiện công việc":["A1","A2","A3","A4","A5","B1","B2","B3","B4","B5","C1","C2","C3","C4","C5","D11","D12","D13","D14","D15","D21","D22","D23","D24","D25","D31","D32","D33","D34","D35","E1","E2","E3","E4","E5","F1","F2","F3","F4","F5"],"Trách nhiệm giám sát & quản lý":["A","B1","B2","B3","C11","C12","C13","C21","C22","C23","C31","C32","C33","D11","D12","D13","D21","D22","D23","D31","D32","D33","E11","E12","E13","E21","E22","E23","E31","E32","E33","F11","F12","F13","F21","F22","F23","F31","F32","F33","G11","G12","G13","G21","G22","G23","G31","G32","G33","H11","H12","H13","H21","H22","H23","H31","H32","H33"],"Tầm ảnh hưởng của các quyết định":["A1","B1","B2","B3","C1","C2","C3","D1","D2","D3","E1","E2","E3","F1","F2","F3","NA"],"Quyền hạn":["A0","A1","A2","A3","B0","B1","B2","B3","C0","C1","C2","C3","D0","D1","D2","D3","E0","E1","E2","E3","NA"],"Môi trường làm việc":["A1","A2","A3","B1","B2","B3","C1","C2","C3","D1","D2","D3","E1","E2","E3","NA"],"Yêu cầu thể lực đối với công việc":["A1","A2","A3","A4","B1","B2","B3","B4","C1","C2","C3","C4","D1","D2","D3","D4","NA"]}

S_GRADE_MAPPING = [
    (195,320,"S1"),(321,420,"S2"),(421,520,"S3"),(521,620,"S4"),
    (621,720,"S5"),(721,870,"S6"),(871,1000,"S7"),(1001,1200,"S8"),
    (1201,1400,"S9"),(1401,1600,"S10"),(1601,1800,"S11"),
    (1801,2200,"S12"),(2201,3000,"S13"),
]

FACTOR_NAMES = [
    "Trình độ học vấn","Kinh nghiệm",
    "Mức độ phức tạp của công việc","Phạm vi công việc",
    "Mức độ giải quyết vấn đề","Mức độ cần được chỉ dẫn, giám sát",
    "Mức độ liên lạc khi thực hiện công việc","Trách nhiệm giám sát & quản lý",
    "Tầm ảnh hưởng của các quyết định","Quyền hạn",
    "Môi trường làm việc","Yêu cầu thể lực đối với công việc",
]
FACTOR_TYPES = [
    "simple","simple","multiplier","multiplier",
    "simple","simple","matrix","matrix",
    "matrix","matrix","matrix","matrix",
]

def get_grade_score(factor_name, grade, f1_score=0, f2_score=0):
    fi = FACTOR_NAMES.index(factor_name) if factor_name in FACTOR_NAMES else -1
    if fi < 0: return 0.0
    ftype = FACTOR_TYPES[fi]
    data = SCORING_LOOKUP.get(factor_name, {}).get(grade, {})
    if not data: return 0.0
    if ftype == "simple":
        return float(data.get("score", 0))
    elif ftype == "multiplier":
        return round((f1_score + f2_score) * float(data.get("multiplier", 0)), 2)
    elif ftype == "matrix":
        return float(data.get("score", 0))
    return 0.0

def get_grade_desc(factor_name, grade):
    data = SCORING_LOOKUP.get(factor_name, {}).get(grade, {})
    if not data: return ""
    if "desc" in data: return data["desc"]
    elif "desc_row" in data: return data["desc_row"] + " / " + data.get("desc_col","")
    return ""

def compute_total_score(factors_dict):
    f1 = get_grade_score("Trình độ học vấn", factors_dict.get("Trình độ học vấn",""))
    f2 = get_grade_score("Kinh nghiệm", factors_dict.get("Kinh nghiệm",""))
    total = f1 + f2
    for fname in FACTOR_NAMES[2:]:
        total += get_grade_score(fname, factors_dict.get(fname,""), f1, f2)
    return round(total, 1)

def score_to_sgrade(total):
    for mn, mx, sg in S_GRADE_MAPPING:
        if mn <= total <= mx: return sg
    return ""

# ── GitHub History Storage ───────────────────────────────────────────────────────
# Lịch sử đánh giá được lưu vào file history.json ngay trong repo qua GitHub API.
# Nhờ đó dữ liệu BỀN VỮNG: còn nguyên khi tải lại trang hoặc mở ở trình duyệt khác.
# Cần cấu hình 2 secrets trên Streamlit Cloud:  GITHUB_REPO="user/repo"  +  GITHUB_TOKEN="ghp_..."
HISTORY_FILE = "history.json"

def _gh_config():
    return st.secrets.get("GITHUB_REPO", ""), st.secrets.get("GITHUB_TOKEN", "")

def github_enabled():
    repo, token = _gh_config()
    return bool(repo and token)

def load_history_from_github():
    """Tải lịch sử từ GitHub. Trả về (history, sha, error). error="" nếu thành công."""
    repo, token = _gh_config()
    if not (repo and token):
        return [], "", "Chưa cấu hình GITHUB_REPO / GITHUB_TOKEN"
    try:
        url = f"https://api.github.com/repos/{repo}/contents/{HISTORY_FILE}"
        req = urllib.request.Request(url, headers={"Authorization": f"token {token}", "User-Agent": "sgrade"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
        decoded = base64.b64decode(data["content"].replace("\n", "")).decode()
        return json.loads(decoded), data.get("sha", ""), ""
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return [], "", ""  # file chưa tồn tại → coi như lịch sử rỗng (lần lưu đầu sẽ tạo file)
        return [], "", f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        return [], "", str(e)

def save_history_to_github(history, sha=""):
    """Ghi đè history.json. Trả về (new_sha, error). error="" nếu thành công."""
    repo, token = _gh_config()
    if not (repo and token):
        return "", "Chưa cấu hình GITHUB_REPO / GITHUB_TOKEN"
    try:
        url = f"https://api.github.com/repos/{repo}/contents/{HISTORY_FILE}"
        payload = {
            "message": "Update S-Grade history",
            "content": base64.b64encode(json.dumps(history, ensure_ascii=False, indent=2).encode()).decode(),
        }
        if sha:
            payload["sha"] = sha
        req = urllib.request.Request(url,
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"token {token}", "Content-Type": "application/json", "User-Agent": "sgrade"},
            method="PUT")
        with urllib.request.urlopen(req, timeout=12) as r:
            resp = json.loads(r.read())
            return resp.get("content", {}).get("sha", ""), ""
    except urllib.error.HTTPError as e:
        # 409/422 = xung đột sha (file đã bị thay đổi bởi lần lưu khác)
        return "", f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        return "", str(e)

def push_history_item(item, max_retries=4):
    """Thêm 1 vị trí vào lịch sử một cách an toàn cho nhiều người dùng đồng thời:
    luôn tải bản mới nhất + sha hiện tại, nối thêm item, rồi lưu. Nếu sha xung đột
    (có người vừa lưu trước) thì tải lại và thử lại — tránh ghi đè mất dữ liệu.
    Trả về (merged_history, new_sha, error). merged_history=None nếu thất bại."""
    if not github_enabled():
        return None, "", "Chưa cấu hình GITHUB_REPO / GITHUB_TOKEN"
    last_err = ""
    for _ in range(max_retries):
        history, sha, err = load_history_from_github()
        if err:
            last_err = err
            continue
        # Upsert: ghi đè nếu đã có cùng title
        merged = [h for h in history if h.get("title") != item.get("title")]
        merged.append(item)
        new_sha, save_err = save_history_to_github(merged, sha)
        if new_sha:
            return merged, new_sha, ""
        last_err = save_err or "Xung đột khi lưu"
        # vòng lặp sẽ tải lại sha mới nhất rồi thử lại
    return None, "", last_err

st.set_page_config(page_title="S-Grade SCOMMERCE", page_icon="📋", layout="wide", initial_sidebar_state="collapsed")

# ── Load databases ──────────────────────────────────────────────────────────────
@st.cache_data
def load_je_database():
    import os
    db_path = os.path.join(os.path.dirname(__file__), "je_data.json")
    if os.path.exists(db_path):
        with open(db_path, encoding="utf-8") as f:
            return json.load(f)
    return []

@st.cache_data
def load_positions():
    import os
    db_path = os.path.join(os.path.dirname(__file__), "sgrade_positions.json")
    if os.path.exists(db_path):
        with open(db_path, encoding="utf-8") as f:
            return json.load(f)
    return []

JE_DATABASE = load_je_database()
POSITIONS = load_positions()

# ── Session state init ──────────────────────────────────────────────────────────
if "history" not in st.session_state:
    _hist, _sha, _err = load_history_from_github()
    st.session_state.history = _hist
    st.session_state.history_sha = _sha
    st.session_state.history_load_err = _err
if "selected_history" not in st.session_state:
    st.session_state.selected_history = None

# ── PwC System Prompt ───────────────────────────────────────────────────────────
PWC_SYSTEM_PROMPT = """<context>
Bạn là chuyên gia đánh giá công việc chuyên sâu, sử dụng phương pháp PwC đã được chuẩn hóa nội bộ tại GHN.
Phương pháp bao gồm 12 yếu tố đánh giá giá trị công việc, mỗi yếu tố có các mức phân loại cụ thể (A, B, C, D...) đi kèm mô tả chi tiết.
</context>

<factor name="Trình độ học vấn">
  <level grade="A">Không yêu cầu kiến thức phổ thông và khả năng đọc/viết.</level>
  <level grade="B">Hoàn thành cấp tiểu học, kỹ năng đọc viết và tính toán đơn giản.</level>
  <level grade="C">Hoàn thành cấp THCS, viết văn bản và tính toán nâng cao.</level>
  <level grade="D">Hoàn thành cấp THPT, sử dụng máy tính.</level>
  <level grade="E">Hoàn thành khóa đào tạo nghề từ 3 tháng đến dưới 1 năm.</level>
  <level grade="F1">Tốt nghiệp Trung cấp nghề chuyên ngành bất kỳ.</level>
  <level grade="F2">Tốt nghiệp Trung cấp nghề chuyên ngành cụ thể.</level>
  <level grade="G1">Tốt nghiệp Cao đẳng chuyên ngành bất kỳ.</level>
  <level grade="G2">Tốt nghiệp Cao đẳng chuyên ngành cụ thể.</level>
  <level grade="H1">Tốt nghiệp Đại học chuyên ngành bất kỳ.</level>
  <level grade="H2">Tốt nghiệp Đại học chuyên ngành cụ thể.</level>
  <level grade="I1">Tốt nghiệp đại học và bồi dưỡng nghiệp vụ/văn bằng 2.</level>
  <level grade="I2">Có bằng thạc sĩ chuyên ngành bất kỳ.</level>
  <level grade="I3">Có bằng thạc sĩ chuyên ngành cụ thể.</level>
  <level grade="J">Có bằng Tiến sĩ, kiến thức chuyên sâu.</level>
</factor>
<factor name="Kinh nghiệm">
  <level grade="A">Không đòi hỏi kinh nghiệm, đào tạo trong vài giờ.</level>
  <level grade="B">Công việc đơn giản, có thể học trong 1 tháng.</level>
  <level grade="C">Quen thuộc công việc không phức tạp. (3 tháng)</level>
  <level grade="D">Công việc thường lệ, cần kinh nghiệm xử lý ngoại lệ. (6 tháng)</level>
  <level grade="E">Kinh nghiệm thực hành thành thạo một kỹ năng. (12 tháng)</level>
  <level grade="F">Kinh nghiệm trong lĩnh vực cụ thể, đào tạo chuyên ngành. (1-2 năm)</level>
  <level grade="G1">Tối thiểu 3 năm kinh nghiệm chuyên môn, không có kinh nghiệm giám sát.</level>
  <level grade="G2">Tối thiểu 5 năm chuyên môn HOẶC 1 năm giám sát nhóm.</level>
  <level grade="G3">Tối thiểu 2-3 năm kinh nghiệm giám sát nhóm.</level>
  <level grade="H1">Tối thiểu 6 năm kinh nghiệm chuyên môn.</level>
  <level grade="H2">Tối thiểu 8 năm chuyên môn VÀ/HOẶC 1 năm quản lý cấp phòng.</level>
  <level grade="H3">Tối thiểu 2-3 năm kinh nghiệm quản lý cấp phòng.</level>
  <level grade="I1">Tối thiểu 10 năm kinh nghiệm chuyên môn.</level>
  <level grade="I2">Kinh nghiệm quản lý đồng thời nhiều phòng ban.</level>
  <level grade="I3">Kinh nghiệm ở cấp điều hành mảng chức năng chủ chốt (GĐ Khối/Phó TGĐ).</level>
  <level grade="J">TGĐ tổ chức nhỏ/vừa, một lĩnh vực.</level>
  <level grade="K">TGĐ tổ chức lớn, nhiều lĩnh vực hoặc nhiều quốc gia.</level>
  <level grade="L">TGĐ tổ chức lớn, nhiều lĩnh vực, nhiều quốc gia trên thế giới.</level>
</factor>
<factor name="Mức độ phức tạp của công việc">
  <level grade="A1-A3">Công việc đơn giản, lặp đi lặp lại, không đòi hỏi suy nghĩ độc lập.</level>
  <level grade="B1-B3">Ứng dụng kiến thức và kỹ năng đã có, công việc cụ thể rõ ràng.</level>
  <level grade="C1-C3">Có chính sách và thủ tục chi tiết, thỉnh thoảng cần ý kiến độc lập.</level>
  <level grade="D1-D3">Yêu cầu rõ về kết quả, chưa có cách thức; cần dung hòa yêu cầu đa bên.</level>
  <level grade="E1-E3">Yêu cầu cao về sáng tạo và thích nghi; kiểm soát mạng chức năng liên kết.</level>
  <level grade="F1-F3">Điều phối và quản lý nhiều chức năng chuyên môn hóa cao.</level>
</factor>
<factor name="Phạm vi công việc">
  <level grade="A">Thực hiện nhiệm vụ cụ thể, không cần giám sát hay phối hợp. (Individual Contributor)</level>
  <level grade="B">Không giám sát, nhưng cần phối hợp với các bộ phận khác.</level>
  <level grade="C">Giám sát các cá nhân khác để đạt mục tiêu cụ thể. (Trưởng nhóm)</level>
  <level grade="D">Quản lý một phần hoạt động của một chức năng. (Trưởng phòng)</level>
  <level grade="E">Quản lý toàn bộ một mảng chức năng. (Giám đốc ban/trung tâm)</level>
  <level grade="F">Phối hợp và quản lý nhiều chức năng liên kết. (GĐ Khối/Phó TGĐ)</level>
  <level grade="G">Kiểm soát, định hướng toàn bộ tổ chức trực thuộc tập đoàn. (TGĐ công ty con)</level>
  <level grade="H">TGĐ tổ chức lớn, ảnh hưởng kiểm soát tất cả định hướng chiến lược. (TGĐ công ty mẹ)</level>
</factor>
<factor name="Mức độ giải quyết vấn đề">
  <level grade="A1-A3">Vấn đề nhỏ, giải quyết bằng lựa chọn đơn giản đã học.</level>
  <level grade="B1-B3">Công việc thường lệ, vấn đề phức tạp hơn, cần vận dụng kiến thức tiền lệ.</level>
  <level grade="C1-C3">Vấn đề đa dạng, cần nghiên cứu và sáng tạo trong phân tích.</level>
  <level grade="D1-D3">Vấn đề trong nhóm/phòng có yếu tố bất thường, cần sáng tạo và phán đoán.</level>
  <level grade="E1-E3">Vấn đề phức tạp ở quy mô một chức năng, cần đánh giá nhiều giải pháp.</level>
  <level grade="F1-F3">Vấn đề phức tạp nhiều chức năng, giải pháp có thể thay đổi chính sách hiện hữu.</level>
  <level grade="G1-G3">Vấn đề mới lạ, cần cách tiếp cận hoàn toàn độc lập, tạo chính sách và chiến lược mới.</level>
  <level grade="H1-H3">Vấn đề ảnh hưởng sâu rộng đến toàn tổ chức hoặc xã hội.</level>
</factor>
<factor name="Mức độ cần được chỉ dẫn/giám sát">
  <level grade="A1-A3">Giám sát chặt chẽ, tất cả công việc đều được kiểm tra chi tiết.</level>
  <level grade="B1-B3">Có chỉ dẫn chi tiết, tự sắp xếp thứ tự, công việc được giám sát hầu hết.</level>
  <level grade="C1-C3">Tuân thủ quy định, được hướng dẫn và ra soát định kỳ.</level>
  <level grade="D1-D3">Mục tiêu rõ ràng, được chỉ dẫn chung, không kiểm tra thường xuyên.</level>
  <level grade="E1-E3">Tự lên kế hoạch cho phòng ban, kiểm tra rất ít, làm việc độc lập.</level>
  <level grade="F1-F3">Tham gia thảo luận mục tiêu mảng, tự lên kế hoạch thực hiện.</level>
  <level grade="G1-G3">Đưa ra mục tiêu cho nhóm chức năng, ra quyết định hoàn toàn độc lập.</level>
  <level grade="H1-H3">Trách nhiệm giới hạn bởi chính sách HĐQT, tự đưa ra mục tiêu cho cả tổ chức.</level>
</factor>
<factor name="Mức độ liên lạc khi thực hiện công việc">
  <level grade="A1-A5">Liên hệ chỉ cho mục đích xã giao.</level>
  <level grade="B1-B5">Trao đổi công việc nội bộ tổ chức.</level>
  <level grade="C1-C5">Cộng tác với bộ phận khác để đạt mục đích chung.</level>
  <level grade="D11-D35">Giám sát/quản lý cấp nhóm, phòng, ban/trung tâm.</level>
  <level grade="E1-E5">Liên hệ phạm vi rộng với phần lớn chức năng, lãnh đạo và điều phối.</level>
  <level grade="F1-F5">Liên hệ cấp quốc tế, điều phối chức năng chiến lược.</level>
</factor>
<factor name="Trách nhiệm giám sát và quản lý">
  <level grade="A">Không quản lý nhân viên.</level>
  <level grade="B1-B3">Giám sát mức thấp, hỗ trợ nhân viên mới hoặc quản lý 1 nhân viên.</level>
  <level grade="C11-C33">Giám sát/quản lý 2-10 nhân sự.</level>
  <level grade="D11-D33">Giám sát/quản lý 11-30 nhân sự.</level>
  <level grade="E11-E33">Giám sát/quản lý 31-100 nhân sự.</level>
  <level grade="F11-F33">Giám sát/quản lý 101-500 nhân sự.</level>
  <level grade="G11-G33">Giám sát/quản lý 501-2000 nhân sự.</level>
  <level grade="H11-H33">Giám sát/quản lý 2000+ nhân sự.</level>
</factor>
<factor name="Ảnh hưởng của các quyết định">
  <level grade="A1">Quyết định không gây thiệt hại hoặc có thể làm lại với nguồn lực không đáng kể.</level>
  <level grade="B1-B3">Nguy cơ lãng phí thấp dưới 2 triệu VND.</level>
  <level grade="C1-C3">Nguy cơ tổn thất tài chính nhỏ dưới 50 triệu VND.</level>
  <level grade="D1-D3">Nguy cơ tổn thất tài chính lớn trên 50 triệu VND.</level>
  <level grade="E1-E3">Quyết định tầm doanh nghiệp, ảnh hưởng vị thế thị trường và lợi nhuận.</level>
  <level grade="F1-F3">Quyết định có thể trực tiếp dẫn đến phá sản và ngừng kinh doanh.</level>
  <level grade="NA">Không áp dụng.</level>
</factor>
<factor name="Quyền hạn">
  <level grade="A0-A3">Không có quyền phê duyệt tài chính.</level>
  <level grade="B0-B3">Được duyệt một phần ngân sách.</level>
  <level grade="C0-C3">Được duyệt toàn bộ ngân sách.</level>
  <level grade="D0-D3">Được duyệt ngoài ngân sách tối đa 5%.</level>
  <level grade="E0-E3">Được duyệt ngoài ngân sách trên 5%.</level>
  <level grade="NA">Không áp dụng.</level>
</factor>
<factor name="Môi trường làm việc">
  <level grade="A1-A3">Trong nhà, điều kiện văn phòng.</level>
  <level grade="B1-B3">Trong nhà, điều kiện dễ chịu, đôi khi ảnh hưởng môi trường.</level>
  <level grade="C1-C3">Trong nhà với ảnh hưởng khó chịu: tiếng ồn, nhiệt độ, chất bẩn.</level>
  <level grade="D1-D3">Phần lớn ngoài trời, không phải thời tiết khắc nghiệt.</level>
  <level grade="E1-E3">Hầu hết ngoài trời, liên tục chịu ảnh hưởng khí hậu đa dạng.</level>
  <level grade="NA">Không áp dụng.</level>
</factor>
<factor name="Yêu cầu thể chất">
  <level grade="A1-A4">Thường ở tư thế ngồi.</level>
  <level grade="B1-B4">Phần lớn đứng và/hoặc đi lại.</level>
  <level grade="C1-C4">Có giai đoạn ngắn cúi, uốn, quỳ, trèo.</level>
  <level grade="D1-D4">Thường xuyên phải cúi gập, uốn người, quỳ hoặc trèo.</level>
  <level grade="NA">Không áp dụng.</level>
</factor>

QUAN TRỌNG:
- Chỉ trả về JSON thuần túy, KHÔNG dùng markdown
- Bắt đầu ngay bằng { và kết thúc bằng }
- Mỗi trường "reason" và "evidence" tối đa 80 từ
- Phải trả về đủ 12 yếu tố

{
  "factors": [
    {"name": "Tên yếu tố", "grade": "Mức xếp loại", "reason": "Lý do ngắn gọn", "evidence": "Dẫn chứng từ JD"}
  ],
  "similar_jobs": [
    {"title": "Tên vị trí tương đồng", "similarity": 85, "reason": "Lý do tương đồng"}
  ],
  "summary": "Nhận xét tổng quan về phạm vi, độ phức tạp và mức độ ảnh hưởng"
}"""

COMPARE_PROMPT = """Bạn là chuyên gia đánh giá công việc PwC. Nhiệm vụ: so sánh vị trí mới với danh sách vị trí đã được đánh giá trong lịch sử.

Trả về JSON thuần túy (không markdown):
{
  "comparisons": [
    {
      "title": "Tên vị trí trong lịch sử",
      "similarity_score": 85,
      "matching_factors": ["Yếu tố 1", "Yếu tố 2"],
      "differing_factors": ["Yếu tố 3"],
      "explanation": "Giải thích chi tiết sự tương đồng và khác biệt, tối đa 100 từ"
    }
  ],
  "overall_insight": "Nhận xét tổng quan về vị trí mới so với toàn bộ danh sách đã có, tối đa 80 từ"
}"""

# ── CSS ─────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700;800;900&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 0 !important; max-width: 1400px; padding-left: 2rem !important; padding-right: 2rem !important; }
.topnav { background:white; border-bottom:1px solid #e8e8e8; padding:0 2rem; height:56px; display:flex; align-items:center; justify-content:space-between; margin:-1rem -1rem 0 -1rem; position:sticky; top:0; z-index:999; }
.topnav-logo { font-size:15px; font-weight:600; color:#1f2937; display:flex; align-items:center; gap:8px; }
.topnav-logo .sc { color:#F26522; font-weight:800; }
.topnav-logo .sep { color:#9ca3af; }
.hero-banner { background:linear-gradient(135deg,#fff0e8 0%,#f0f4ff 100%); border-radius:20px; padding:2.5rem 3rem; margin:1.5rem 0 1.5rem; }
.hero-sub { font-size:13px; font-weight:600; color:#6b7280; letter-spacing:0.08em; text-transform:uppercase; margin-bottom:0.5rem; }
.hero-title { font-family:'Barlow Condensed',sans-serif; font-size:64px; font-weight:900; color:#F26522; line-height:0.95; text-transform:uppercase; margin-bottom:0.5rem; }
.hero-tagline { font-family:'Barlow Condensed',sans-serif; font-size:20px; font-weight:700; color:#F26522; text-transform:uppercase; letter-spacing:0.04em; }
.summary-box { background:#f0faf5; border:1px solid #b7e8d0; border-radius:10px; padding:1.25rem 1.5rem; margin:1rem 0; }
.summary-box h4 { font-size:14px; font-weight:600; color:#1a7a4a; margin:0 0 0.5rem; }
.summary-box p { font-size:14px; color:#2d6a4f; line-height:1.7; margin:0; }
.similar-item { display:flex; align-items:center; gap:12px; background:#f5f5f5; border-radius:8px; padding:10px 14px; margin-bottom:6px; font-size:13px; }
.sim-pct { background:#fff4ee; color:#d4551a; font-weight:700; font-size:13px; padding:2px 10px; border-radius:6px; flex-shrink:0; }
.history-card { background:white; border:1px solid #e8e8e8; border-radius:10px; padding:1rem 1.25rem; margin-bottom:0.75rem; cursor:pointer; transition:border-color 0.15s; }
.history-card:hover { border-color:#F26522; }
.history-card-title { font-weight:600; font-size:15px; color:#1f2937; margin-bottom:4px; }
.history-card-meta { font-size:12px; color:#9ca3af; }
.grade-chips { display:flex; flex-wrap:wrap; gap:4px; margin-top:8px; }
.chip { font-size:11px; font-weight:600; padding:2px 8px; border-radius:999px; }
.compare-card { background:white; border:1px solid #e8e8e8; border-radius:10px; padding:1.25rem; margin-bottom:0.75rem; }
.compare-pct-bar { height:8px; border-radius:4px; background:#F26522; margin-top:6px; }
.stButton>button { border-radius:999px !important; font-family:'Plus Jakarta Sans',sans-serif !important; font-weight:600 !important; font-size:14px !important; }
div[data-testid="column"]:first-child .stButton>button { background:#F26522 !important; color:white !important; border:none !important; }
.topnav { position:sticky !important; top:0 !important; z-index:999 !important; }
</style>
""", unsafe_allow_html=True)

# ── Helpers ──────────────────────────────────────────────────────────────────────
def grade_color(g):
    g = str(g).upper()
    if g.startswith("A"): return "#1a7a4a", "#f0faf5"
    if g.startswith("B"): return "#185fa5", "#e6f1fb"
    if g.startswith("C"): return "#854f0b", "#faeeda"
    if g.startswith("D"): return "#993556", "#fbeaf0"
    if g.startswith("E"): return "#993c1d", "#faece7"
    if g.startswith("F"): return "#5b21b6", "#ede9fe"
    if g.startswith("G"): return "#065f46", "#d1fae5"
    return "#444441", "#f1efe8"

def fix_json(raw):
    s = raw.strip().lstrip('\ufeff')
    start = s.find('{')
    if start == -1:
        raise ValueError("No JSON found")
    s = s[start:]
    depth = 0
    in_str = False
    escape = False
    last_valid = 0
    for i, ch in enumerate(s):
        if escape: escape = False; continue
        if ch == '\\': escape = True; continue
        if ch == '"': in_str = not in_str
        if not in_str:
            if ch in '{[': depth += 1
            elif ch in '}]':
                depth -= 1
                if depth == 0: last_valid = i
    if depth == 0:
        return json.loads(s[:last_valid+1])
    fixed = re.sub(r',\s*\{[^}]*$', '', s)
    fixed = re.sub(r',\s*"[^"]*":\s*"[^"]*$', '', fixed)
    if fixed.rstrip().endswith(','):
        fixed = fixed.rstrip().rstrip(',')
    o = fixed.count('{') - fixed.count('}')
    a = fixed.count('[') - fixed.count(']')
    fixed += ']' * max(0,a) + '}' * max(0,o)
    return json.loads(fixed)

def _normalize_factor_name(name):
    name = name.strip()
    if name in FACTOR_NAMES: return name
    name_lower = name.lower()
    for fn in FACTOR_NAMES:
        if fn.lower() in name_lower or name_lower in fn.lower(): return fn
        words = set(name_lower.replace(",","").replace("/","").split())
        fn_words = set(fn.lower().replace(",","").replace("/","").split())
        if len(words & fn_words) >= 2: return fn
    return name

def render_result_table(factors, job_title, adjustments=None, show_adjust=False, key_prefix=""):
    import pandas as pd
    if adjustments is None:
        adjustments = {}

    normalized_factors = []
    for f in factors:
        nf = dict(f)
        nf["_norm"] = _normalize_factor_name(f.get("name",""))
        normalized_factors.append(nf)

    sk = f"adj_state_{key_prefix}"
    if sk not in st.session_state:
        st.session_state[sk] = {f["_norm"]: adjustments.get(f["_norm"], f.get("grade","")) for f in normalized_factors}
    current_adj = st.session_state[sk]

    grades_dict = {f["_norm"]: current_adj.get(f["_norm"], f.get("grade","")) for f in normalized_factors}
    f1 = get_grade_score("Trình độ học vấn", grades_dict.get("Trình độ học vấn",""))
    f2 = get_grade_score("Kinh nghiệm", grades_dict.get("Kinh nghiệm",""))
    total_score = round(compute_total_score(grades_dict))
    computed_sgrade = score_to_sgrade(total_score)

    # Header
    st.markdown(f"""<div style="background:#1f2937;border-radius:12px 12px 0 0;padding:0.875rem 1.5rem;
      display:flex;justify-content:space-between;align-items:center;margin-top:0.5rem">
      <span style="color:white;font-weight:600;font-size:15px">Kết quả đánh giá: {html.escape(job_title)}</span>
      <span style="color:#9ca3af;font-size:13px">Tổng: <strong style="color:#F26522">{total_score}</strong>
        &rarr; <strong style="color:#F26522">{computed_sgrade}</strong></span>
    </div>""", unsafe_allow_html=True)

    # Build display table as HTML (read-only part)
    rows = ""
    row_data = []
    for i, f in enumerate(normalized_factors):
        fname    = f["_norm"]
        ai_grade = f.get("grade","")
        adj_grade= current_adj.get(fname, ai_grade)
        disp_gr  = adj_grade
        score    = get_grade_score(fname, disp_gr, f1, f2)
        tc, bg   = grade_color(ai_grade)
        adj_tc, adj_bg = grade_color(adj_grade)
        desc     = get_grade_desc(fname, adj_grade)
        short_d  = html.escape(desc)
        score_s  = str(round(score))
        reason   = html.escape(str(f.get("reason",""))[:260])
        evidence = html.escape(str(f.get("evidence",""))[:260])
        is_adj   = adj_grade != ai_grade
        badge    = '<span style="font-size:9px;background:#fef3c7;color:#92400e;padding:1px 3px;border-radius:2px;margin-left:2px">↑</span>' if is_adj else ""
        available= FACTOR_GRADES.get(fname, list(SCORING_LOOKUP.get(fname, {}).keys()))

        adj_span = f'<span style="display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:50%;background:{adj_bg};color:{adj_tc};font-weight:700;font-size:11px">{html.escape(adj_grade)}</span>' if is_adj else ""

        rows += f"""<tr style="border-bottom:1px solid #f0f0f0;background:white">
<td style="padding:9px 11px;font-size:12px;font-weight:600;color:#1f2937;vertical-align:top;width:16%">{html.escape(f.get("name",""))}</td>
<td style="padding:9px 11px;font-size:12px;color:#374151;vertical-align:top;width:23%;line-height:1.5">{reason}</td>
<td style="padding:9px 11px;font-size:12px;font-style:italic;color:#4b5563;vertical-align:top;width:27%;line-height:1.5">{evidence}</td>
<td style="padding:9px 11px;text-align:center;vertical-align:top;width:7%"><span style="display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:50%;background:{bg};color:{tc};font-weight:700;font-size:11px">{html.escape(ai_grade)}</span>{badge}</td>
<td style="padding:9px 11px;font-size:11px;color:#6b7280;vertical-align:top;width:20%;line-height:1.4;word-wrap:break-word;white-space:normal">{short_d}</td>
<td style="padding:9px 11px;text-align:center;font-weight:700;font-size:13px;color:#F26522;vertical-align:top;width:6%">{score_s}</td>
{"<td style='padding:9px 11px;text-align:center;vertical-align:top;width:7%'>" + adj_span + "</td>" if show_adjust else ""}
</tr>"""
        row_data.append((fname, f.get("name",""), ai_grade, adj_grade, available))

    adj_col = "<th style='padding:8px 11px;text-align:center;font-size:11px;font-weight:600;color:#374151;width:7%'>Điều chỉnh</th>" if show_adjust else ""
    st.markdown(f"""<div style="background:white;border-radius:0 0 12px 12px;overflow:hidden;border:1px solid #e8e8e8;border-top:none">
<table style="width:100%;border-collapse:collapse;background:white;table-layout:fixed">
<thead><tr style="background:#f3f4f6;border-bottom:2px solid #e5e7eb">
<th style="padding:8px 11px;text-align:left;font-size:11px;font-weight:600;color:#374151;width:16%">Yếu tố</th>
<th style="padding:8px 11px;text-align:left;font-size:11px;font-weight:600;color:#374151;width:23%">Lý do</th>
<th style="padding:8px 11px;text-align:left;font-size:11px;font-weight:600;color:#374151;width:27%">Dẫn chứng</th>
<th style="padding:8px 11px;text-align:center;font-size:11px;font-weight:600;color:#374151;width:7%">Mức AI</th>
<th style="padding:8px 11px;text-align:left;font-size:11px;font-weight:600;color:#374151;width:17%">Định nghĩa</th>
<th style="padding:8px 11px;text-align:center;font-size:11px;font-weight:600;color:#374151;width:6%">Điểm</th>
{adj_col}
</tr></thead><tbody>{rows}</tbody></table></div>""", unsafe_allow_html=True)

    if not show_adjust:
        return None

    # Điều chỉnh — selectbox riêng từng tiêu chí (tránh flicker của data_editor)
    st.markdown("<div style='margin-top:1rem;font-size:13px;font-weight:600;color:#374151;margin-bottom:4px'>⚙️ Điều chỉnh mức chấm</div>", unsafe_allow_html=True)

    new_adjustments = dict(current_adj)

    for fname, orig_name, ai_grade, adj_grade, available in row_data:
        cur_val = current_adj.get(fname, ai_grade) or ai_grade
        # Tạo options với label đầy đủ định nghĩa
        def _opt_label(g, fn):
            data = SCORING_LOOKUP.get(fn, {}).get(g, {})
            if not data: return g
            if "desc" in data:
                return f"{g} — {data['desc'][:80]}"
            elif "desc_row" in data:
                return f"{g} — {data['desc_row'][:50]} / {data.get('desc_col','')[:40]}"
            return g

        options_keys = available  # list mức chấm hợp lệ
        options_labels = [_opt_label(g, fname) for g in options_keys]

        # Tìm index hiện tại
        try:
            cur_idx = options_keys.index(cur_val)
        except ValueError:
            cur_idx = 0

        with st.expander(f"**{orig_name}** — Mức AI: `{ai_grade}`" + (" ✏️" if cur_val != ai_grade else ""), expanded=False):
            # Hiện định nghĩa mức AI để tham chiếu
            ai_desc = get_grade_desc(fname, ai_grade)
            if ai_desc:
                st.caption(f"📌 Định nghĩa mức AI ({ai_grade}): {ai_desc}")

            safe_fname = re.sub(r'[^a-zA-Z0-9]', '_', fname)
            chosen_label = st.selectbox(
                "Chọn mức điều chỉnh",
                options=options_labels,
                index=cur_idx,
                key=f"sel_{key_prefix}_{safe_fname}",
                label_visibility="collapsed",
            )
            chosen_grade = options_keys[options_labels.index(chosen_label)]

            if chosen_grade != ai_grade:
                new_adjustments[fname] = chosen_grade
                new_desc = get_grade_desc(fname, chosen_grade)
                if new_desc:
                    st.info(f"✅ Mức đã chọn ({chosen_grade}): {new_desc}")
            else:
                new_adjustments[fname] = ai_grade

    st.session_state[sk] = new_adjustments

    # Tính lại điểm ngay sau khi data_editor cập nhật
    new_grades = {f["_norm"]: new_adjustments.get(f["_norm"], f.get("grade","")) for f in normalized_factors}
    new_f1 = get_grade_score("Trình độ học vấn", new_grades.get("Trình độ học vấn",""))
    new_f2 = get_grade_score("Kinh nghiệm", new_grades.get("Kinh nghiệm",""))
    new_total = round(compute_total_score(new_grades))
    new_sg = score_to_sgrade(new_total)

    has_adj = any(new_adjustments.get(f["_norm"], f.get("grade","")) != f.get("grade","") for f in normalized_factors)
    label_c = "#F26522" if new_total != total_score else "#6b7280"

    col_score, col_btn = st.columns([4, 1])
    with col_score:
        if has_adj:
            st.markdown(f"""<div style="background:#fff4ee;border:1px solid #fcd4b8;border-radius:8px;
              padding:0.75rem 1.5rem;margin-top:0.5rem;display:flex;gap:1.5rem;align-items:center">
              <span style="font-size:13px;color:#854f0b">Điểm sau điều chỉnh:</span>
              <strong style="font-size:22px;color:#F26522">{new_total}</strong>
              <span style="color:#9ca3af">&rarr;</span>
              <strong style="font-size:22px;color:#F26522">{new_sg}</strong>
              <span style="font-size:12px;color:#9ca3af">(gốc: {total_score} → {computed_sgrade})</span>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""<div style="background:#f3f4f6;border-radius:8px;
              padding:0.75rem 1.5rem;margin-top:0.5rem;display:flex;gap:1.5rem;align-items:center">
              <span style="font-size:13px;color:#6b7280">Tổng điểm AI:</span>
              <strong style="font-size:22px;color:#1f2937">{total_score}</strong>
              <span style="color:#9ca3af">&rarr;</span>
              <strong style="font-size:22px;color:#1f2937">{computed_sgrade}</strong>
            </div>""", unsafe_allow_html=True)
    with col_btn:
        if st.button("🔄 Cập nhật điểm", key=f"recalc_{key_prefix}", use_container_width=True):
            st.session_state[sk] = new_adjustments
            st.rerun()

    return new_adjustments


def call_gemini(api_key, system_prompt, user_content, max_tokens=8192):
    client = genai.Client(api_key=api_key)
    last_err = None
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=max_tokens,
                    temperature=0.2,
                    response_mime_type="application/json",
                ),
            )
            return response.text
        except Exception as e:
            last_err = e
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                wait = (attempt+1) * 5
                st.toast(f"Server bận, thử lại sau {wait}s... ({attempt+1}/3)")
                time.sleep(wait)
            else:
                raise e
    raise last_err

def get_jd_content(uploaded_file, jd_text_input):
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".txt"):
                return uploaded_file.read().decode("utf-8")
            else:
                try:
                    import docx as _docx
                    doc = _docx.Document(io.BytesIO(uploaded_file.read()))
                    return "\n".join([p.text for p in doc.paragraphs])
                except Exception:
                    return uploaded_file.read().decode("utf-8", errors="ignore")
        except Exception as e:
            st.error(f"Không thể đọc file: {e}")
            return None
    elif jd_text_input.strip():
        return jd_text_input.strip()
    return None

# ── Nav ──────────────────────────────────────────────────────────────────────────
if "main_page" not in st.session_state:
    st.session_state.main_page = "evaluate"

# Nav bar HTML (visual only)
p = st.session_state.main_page
def active(key): return "background:#F26522;color:white;border:none;" if p==key else "background:white;color:#6b7280;border:1px solid #e8e8e8;"

st.markdown(f"""
<div class="topnav">
  <div class="topnav-logo">
    <span class="sc">SCOMMERCE</span><span class="sep">|</span><span>S-Grade SCOMMERCE</span>
  </div>
</div>
""", unsafe_allow_html=True)

# Nav buttons using Streamlit columns (functional)
_, nc1, nc2, nc3, _r = st.columns([3, 1.8, 1.8, 2.2, 0.1])
with nc1:
    if st.button("Đánh giá S-Grade", use_container_width=True, type="primary" if p=="evaluate" else "secondary"):
        st.session_state.main_page = "evaluate"
        st.rerun()
with nc2:
    if st.button("Tra cứu S-Grade", use_container_width=True, type="primary" if p=="lookup" else "secondary"):
        st.session_state.main_page = "lookup"
        st.rerun()
with nc3:
    if st.button("Phúc lợi theo S-Grade", use_container_width=True, type="primary" if p=="benefits" else "secondary"):
        st.session_state.main_page = "benefits"
        st.rerun()

main_page = st.session_state.main_page

# ════════════ PAGE ROUTER ══════════════════════════════════════════════════════

# ── PAGE: ĐÁNH GIÁ S-GRADE ──────────────────────────────────────────────────────
if main_page == "evaluate":

    # ── Hero ─────────────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="hero-banner">
      <div class="hero-sub">Chào mừng bạn đến với</div>
      <div class="hero-title">S-Grade<br>SCOMMERCE</div>
      <div class="hero-tagline">Đánh giá mô tả công việc theo 12 yếu tố PwC</div>
    </div>
    """, unsafe_allow_html=True)
    
    # ── Main Tabs ────────────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(["⚡  Đánh giá JD", "📂  Lịch sử & So sánh", "🗂  Tra cứu S-Grade"])
    
    # ════════════════════════════════════════════════════════════════════════════════
    # TAB 1: ĐÁNH GIÁ
    # ════════════════════════════════════════════════════════════════════════════════
    with tab1:
        job_title = st.text_input("**Nhập tên vị trí công việc**", placeholder="e.g., Deputy Sorting Centers Manager")
        st.markdown("**Tải lên JD (.docx, .txt)**")
        uploaded_file = st.file_uploader("upload", type=["txt","docx","doc"], label_visibility="collapsed")
        st.markdown("<div style='text-align:center;color:#9ca3af;font-size:13px;margin:0.75rem 0'>— hoặc —</div>", unsafe_allow_html=True)
        jd_text_input = st.text_area("**Nhập nội dung JD trực tiếp**", placeholder="Paste nội dung mô tả công việc vào đây...", height=160)
    
        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([2, 1.5, 6])
        with c1:
            eval_btn = st.button("⚡  Đánh giá JD", use_container_width=True)
        with c2:
            clear_btn = st.button("Xóa nội dung", use_container_width=True)
        if clear_btn:
            st.rerun()
    
        if eval_btn:
            if not job_title.strip():
                st.error("⚠️ Vui lòng nhập tên vị trí công việc.")
            else:
                jd_content = get_jd_content(uploaded_file, jd_text_input)
                if not jd_content:
                    st.error("⚠️ Vui lòng tải lên file JD hoặc nhập nội dung JD.")
                else:
                    try:
                        api_key = st.secrets["GEMINI_API_KEY"]
                    except Exception:
                        st.error("❌ Chưa cấu hình GEMINI_API_KEY trong Streamlit Secrets.")
                        st.stop()
    
                    # Context điều chỉnh từ lịch sử
                    adj_ctx = ""
                    past_adjs = [(h["title"], h.get("adjustments",{})) for h in st.session_state.history if h.get("adjustments")]
                    if past_adjs:
                        adj_ctx = "\n\nLƯU Ý từ chuyên gia (tham khảo nếu vị trí tương đồng):\n"
                        for pt, pa in past_adjs[-5:]:
                            lines = [f"  {k}: {v}" for k,v in pa.items() if v]
                            if lines: adj_ctx += f"'{pt}':\n" + "\n".join(lines) + "\n"

                    with st.spinner("🤖 AI đang phân tích 12 yếu tố theo phương pháp PwC..."):
                        try:
                            raw = call_gemini(api_key, PWC_SYSTEM_PROMPT, f"Tên vị trí: {job_title}\n\nNội dung JD:\n{jd_content}{adj_ctx}")
                            result = fix_json(raw)
                            factors = result.get("factors", [])
                            similar = result.get("similar_jobs", [])
                            summary = result.get("summary", "")
    
                            # ── Lưu vào lịch sử (bền vững trên GitHub) ────────────
                            new_item = {
                                "title": job_title,
                                "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                                "jd": jd_content[:2000],
                                "result": result,
                            }
                            # Lưu kết quả vào session để hiển thị sau rerun
                            st.session_state.last_eval = {
                                "title": job_title,
                                "factors": factors,
                                "summary": result.get("summary",""),
                                "similar": result.get("similar_jobs",[]),
                            }
                            # Reset adjustments cho vị trí mới
                            st.session_state[f"adj_{job_title}"] = {}
                            st.session_state[f"adj_state_eval_{job_title[:20]}"] = {}
                            st.session_state["_just_evaled"] = True
                            if github_enabled():
                                merged, new_sha, push_err = push_history_item(new_item)
                                if merged is not None:
                                    # Đồng bộ thành công: session_state phản ánh đúng bản trên GitHub
                                    st.session_state.history = merged
                                    st.session_state.history_sha = new_sha
                                    st.session_state.save_status = ("ok", "")
                                else:
                                    # Lưu lỗi: vẫn giữ tạm trong phiên để không mất kết quả vừa chạy
                                    st.session_state.history.append(new_item)
                                    st.session_state.save_status = ("error", push_err)
                            else:
                                st.session_state.history.append(new_item)
                                st.session_state.save_status = ("not_configured", "")
    
                            # Render sẽ hiện bên ngoài if eval_btn — xem bên dưới
    
                            # ── Export ─────────────────────────────────────────────
                            st.markdown("<br>", unsafe_allow_html=True)
                            e1, e2 = st.columns(2)
                            csv_buf = io.StringIO()
                            writer = csv.writer(csv_buf)
                            writer.writerow(["Vị trí","Yếu tố","Mức","Lý do","Dẫn chứng"])
                            for f in factors:
                                writer.writerow([job_title, f["name"], f["grade"], f["reason"], f["evidence"]])
                            with e1:
                                st.download_button("📥 Xuất CSV", "\ufeff"+csv_buf.getvalue(),
                                    f"sgrade_{job_title.replace(' ','_')}.csv", "text/csv", use_container_width=True)
                            with e2:
                                st.download_button("📄 Xuất JSON", json.dumps(result, ensure_ascii=False, indent=2),
                                    f"sgrade_{job_title.replace(' ','_')}.json", "application/json", use_container_width=True)
    
                            _status, _detail = st.session_state.get("save_status", ("ok", ""))
                            if _status == "ok":
                                st.success("✅ Đã lưu vào lịch sử và đồng bộ GitHub! Kết quả sẽ còn nguyên khi tải lại trang hoặc mở ở trình duyệt khác. Xem tại tab **Lịch sử & So sánh**.")

                                # Lưu điều chỉnh
                                adj_key2 = f"adj_{job_title}"
                                if adj_key2 in st.session_state and st.session_state[adj_key2]:
                                    if st.button("💾 Lưu điều chỉnh lên GitHub", key="save_adj_btn"):
                                        if st.session_state.history:
                                            st.session_state.history[-1]["adjustments"] = st.session_state[adj_key2]
                                            adj_total = compute_total_score(st.session_state[adj_key2])
                                            st.session_state.history[-1]["adjusted_total"] = adj_total
                                            st.session_state.history[-1]["adjusted_sgrade"] = score_to_sgrade(adj_total)
                                            _sha = save_history_to_github(
                                                st.session_state.history,
                                                st.session_state.get("history_sha","")
                                            )
                                            if _sha:
                                                st.session_state.history_sha = _sha
                                                st.success("✅ Đã lưu điều chỉnh lên GitHub!")
                                            else:
                                                st.warning("⚠️ Không lưu được GitHub, kiểm tra token.")
                            elif _status == "not_configured":
                                st.warning("⚠️ Đã đánh giá xong nhưng **chưa cấu hình GITHUB_REPO / GITHUB_TOKEN**, nên kết quả chỉ lưu **tạm trong phiên này** và sẽ mất khi tải lại trang. Xem hướng dẫn cấu hình ở tab **Lịch sử & So sánh**.")
                            else:
                                st.warning(f"⚠️ Đã đánh giá xong nhưng **không lưu được lên GitHub** ({_detail}). Kết quả chỉ lưu tạm trong phiên này. Vui lòng kiểm tra GITHUB_TOKEN còn hiệu lực và có quyền ghi repo.")
    
                        except json.JSONDecodeError:
                            st.error("AI trả về định dạng không hợp lệ. Vui lòng thử lại.")
                            with st.expander("Raw output"):
                                st.text(raw)
                        except Exception as e:
                            st.error(f"🔴 Lỗi: {str(e)}")

        # ── Hiển thị kết quả ngoài if eval_btn — persist qua rerun ──────────
        if "last_eval" in st.session_state and not st.session_state.pop("_just_evaled", False):
            ev = st.session_state.last_eval
            ev_title = ev["title"]
            ev_factors = ev["factors"]
            adj_key = f"adj_{ev_title}"
            adj_sk = f"adj_state_eval_{ev_title[:20]}"
            if adj_key not in st.session_state:
                st.session_state[adj_key] = {}
            if adj_sk not in st.session_state:
                st.session_state[adj_sk] = {}

            new_adj = render_result_table(
                ev_factors, ev_title,
                adjustments=st.session_state[adj_sk],
                show_adjust=True,
                key_prefix=f"eval_{ev_title[:20]}"
            )
            if new_adj is not None:
                st.session_state[adj_sk] = new_adj

            if ev.get("summary"):
                st.markdown(f"""<div class="summary-box" style="margin-top:1rem">
                  <h4>Nhận xét tổng quan</h4><p>{ev["summary"]}</p></div>""", unsafe_allow_html=True)

            if ev.get("similar"):
                st.markdown("#### Các JD có phạm vi tương đồng")
                for j in ev["similar"]:
                    st.markdown(f"""<div class="similar-item">
                      <span class="sim-pct">{j.get("similarity",0)}%</span>
                      <span><strong>{j.get("title","")}</strong> — {j.get("reason","")}</span>
                    </div>""", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════════════
    # TAB 2: LỊCH SỬ & SO SÁNH
    # ════════════════════════════════════════════════════════════════════════════════
    with tab2:
        # ── Thanh trạng thái lưu trữ + nút làm mới ─────────────────────────────────
        hc1, hc2 = st.columns([6, 1.4])
        with hc1:
            if github_enabled():
                st.markdown("<div style='font-size:13px;color:#1a7a4a;padding-top:8px'>🟢 Lịch sử được lưu bền vững trên GitHub — đồng bộ qua mọi trình duyệt.</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div style='font-size:13px;color:#993c1d;padding-top:8px'>🟠 Chưa cấu hình lưu trữ — lịch sử chỉ tồn tại tạm trong phiên này.</div>", unsafe_allow_html=True)
        with hc2:
            if st.button("🔄 Làm mới", use_container_width=True, help="Tải lại lịch sử mới nhất từ GitHub (gồm cả kết quả từ trình duyệt/người khác)"):
                _h, _s, _e = load_history_from_github()
                if _e:
                    st.session_state.history_load_err = _e
                else:
                    st.session_state.history = _h
                    st.session_state.history_sha = _s
                    st.session_state.history_load_err = ""
                st.rerun()

        if not github_enabled():
            with st.expander("⚙️ Cách bật lưu trữ bền vững (qua reload & mọi trình duyệt)"):
                st.markdown("""
Lịch sử cần được lưu phía server thì mới còn nguyên khi tải lại trang hoặc mở ở trình duyệt khác. App này lưu vào file `history.json` ngay trong repo qua GitHub API. Làm 1 lần:

1. **Tạo GitHub Personal Access Token**: vào *GitHub → Settings → Developer settings → Personal access tokens → Fine-grained token*. Cấp quyền **Contents: Read and write** cho đúng repo chứa app này.
2. **Khai báo Secrets trên Streamlit Cloud**: *Manage app → Settings → Secrets*, dán vào:
   ```toml
   GITHUB_REPO  = "YOUR_USERNAME/sgrade-app"
   GITHUB_TOKEN = "github_pat_..."
   ```
3. **Save** → app tự khởi động lại. Lần đánh giá tiếp theo sẽ tự tạo `history.json` và đồng bộ.
""")

        if st.session_state.get("history_load_err"):
            st.warning(f"⚠️ Không tải được lịch sử từ GitHub: {st.session_state.history_load_err}")

        history = st.session_state.history

        if not history:
            st.info("📭 Chưa có vị trí nào được đánh giá. Hãy đánh giá một JD ở tab trước để bắt đầu!")
        else:
            # ── Layout: cột trái = danh sách, cột phải = chi tiết + so sánh ──────
            left_col, right_col = st.columns([1, 2.2], gap="medium")
    
            with left_col:
                st.markdown(f"**{len(history)} vị trí đã đánh giá**")
                st.markdown("<br>", unsafe_allow_html=True)
    
                for i, item in enumerate(reversed(history)):
                    idx = len(history) - 1 - i
                    factors = item["result"].get("factors", [])
                    chips_html = ""
                    for f in factors[:6]:
                        tc, bg = grade_color(f.get("grade",""))
                        chips_html += f'<span class="chip" style="background:{bg};color:{tc}">{f.get("name","")[:8]}: {f.get("grade","")}</span>'
    
                    if st.button(f"📄 {item['title']}", key=f"hist_{idx}", use_container_width=True):
                        st.session_state.selected_history = idx
    
                    st.markdown(f"""<div style="font-size:11px;color:#9ca3af;margin:-8px 0 8px 0">{item['date']}</div>
                    <div class="grade-chips">{chips_html}</div>
                    <div style="margin-bottom:12px"></div>""", unsafe_allow_html=True)
    
            with right_col:
                sel = st.session_state.selected_history
    
                if sel is None:
                    st.markdown("""<div style="background:#f9f9f9;border-radius:12px;padding:3rem;text-align:center;color:#9ca3af;border:1px dashed #e8e8e8">
                      <div style="font-size:32px;margin-bottom:0.5rem">👈</div>
                      <div style="font-size:14px">Chọn một vị trí bên trái để xem chi tiết và so sánh</div>
                    </div>""", unsafe_allow_html=True)
                else:
                    item = history[sel]
                    result = item["result"]
                    factors = result.get("factors", [])
    
                    detail_tab, compare_tab = st.tabs(["📋 Chi tiết 12 yếu tố", "🔍 So sánh tương đồng"])
    
                    # ── Chi tiết ──────────────────────────────────────────────────
                    with detail_tab:
                        render_result_table(factors, item["title"],
                            adjustments=item.get("adjustments",{}),
                            show_adjust=False,
                            key_prefix=f"hist_{sel}")
                        summary = result.get("summary", "")
                        if summary:
                            st.markdown(f"""<div class="summary-box" style="margin-top:1rem">
                              <h4>Nhận xét tổng quan</h4><p>{summary}</p></div>""", unsafe_allow_html=True)
    
                    # ── So sánh ───────────────────────────────────────────────────
                    with compare_tab:
                        if len(history) < 2:
                            st.info("Cần ít nhất 2 vị trí để so sánh. Hãy đánh giá thêm JD!")
                        else:
                            other_items = [h for i2, h in enumerate(history) if i2 != sel]
    
                            if st.button("🔍 Phân tích so sánh với AI", key="run_compare", use_container_width=False):
                                try:
                                    api_key = st.secrets["GEMINI_API_KEY"]
                                except Exception:
                                    st.error("❌ Chưa cấu hình GEMINI_API_KEY.")
                                    st.stop()
    
                                # Build context
                                current_summary = f"""Vị trí cần so sánh: {item['title']}
    Kết quả đánh giá: {json.dumps([{"name": f["name"], "grade": f["grade"]} for f in factors], ensure_ascii=False)}
    Tóm tắt: {result.get("summary", "")}
    Nội dung JD (tóm tắt): {item['jd'][:800]}"""
    
                                history_summary = "\n\n".join([
                                    f"Vị trí: {h['title']}\nGrades: {json.dumps([{'name': f['name'], 'grade': f['grade']} for f in h['result'].get('factors', [])], ensure_ascii=False)}\nTóm tắt: {h['result'].get('summary', '')}"
                                    for h in other_items
                                ])
    
                                user_content = f"{current_summary}\n\n---DANH SÁCH VỊ TRÍ TRONG LỊCH SỬ---\n{history_summary}"
    
                                with st.spinner("🤖 AI đang phân tích tương đồng..."):
                                    try:
                                        raw = call_gemini(api_key, COMPARE_PROMPT, user_content, max_tokens=4096)
                                        cmp_result = fix_json(raw)
                                        comparisons = cmp_result.get("comparisons", [])
                                        insight = cmp_result.get("overall_insight", "")
    
                                        if insight:
                                            st.markdown(f"""<div class="summary-box">
                                              <h4>Nhận xét tổng quan</h4><p>{insight}</p></div>""", unsafe_allow_html=True)
    
                                        comparisons_sorted = sorted(comparisons, key=lambda x: x.get("similarity_score", 0), reverse=True)
                                        for cmp in comparisons_sorted:
                                            score = cmp.get("similarity_score", 0)
                                            tc, bg = grade_color("E" if score >= 80 else "B" if score >= 60 else "A")
                                            matching = ", ".join(cmp.get("matching_factors", []))
                                            differing = ", ".join(cmp.get("differing_factors", []))
    
                                            st.markdown(f"""
                                            <div class="compare-card">
                                              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
                                                <span style="font-weight:600;font-size:14px;color:#1f2937">{cmp.get("title","")}</span>
                                                <span style="display:inline-flex;align-items:center;justify-content:center;width:42px;height:42px;border-radius:50%;background:{bg};color:{tc};font-weight:700;font-size:14px">{score}%</span>
                                              </div>
                                              <div style="background:#e8e8e8;height:6px;border-radius:3px;margin-bottom:10px">
                                                <div style="background:#F26522;height:6px;border-radius:3px;width:{score}%"></div>
                                              </div>
                                              <p style="font-size:13px;color:#374151;line-height:1.6;margin-bottom:8px">{cmp.get("explanation","")}</p>
                                              {"<div style='font-size:12px;color:#1a7a4a;margin-top:4px'>✅ Tương đồng: " + matching + "</div>" if matching else ""}
                                              {"<div style='font-size:12px;color:#993c1d;margin-top:2px'>⚠️ Khác biệt: " + differing + "</div>" if differing else ""}
                                            </div>""", unsafe_allow_html=True)
    
                                    except Exception as e:
                                        st.error(f"🔴 Lỗi so sánh: {str(e)}")
                            else:
                                # Show static grade comparison table
                                st.markdown(f"**So sánh grade nhanh:** {item['title']} vs các vị trí đã đánh giá")
                                factor_names = [f["name"] for f in factors]
                                cur_grades = {f["name"]: f["grade"] for f in factors}
    
                                rows_html = ""
                                for fname in factor_names:
                                    row = f"<td style='padding:7px 10px;font-size:12px;font-weight:500;color:#1f2937;background:white'>{fname}</td>"
                                    tc, bg = grade_color(cur_grades.get(fname,""))
                                    row += f"<td style='padding:7px 10px;text-align:center;background:white'><span style='display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:50%;background:{bg};color:{tc};font-weight:700;font-size:11px'>{cur_grades.get(fname,'')}</span></td>"
                                    for h in other_items[:4]:
                                        h_grades = {f2["name"]: f2["grade"] for f2 in h["result"].get("factors",[])}
                                        g = h_grades.get(fname, "—")
                                        tc2, bg2 = grade_color(g) if g != "—" else ("#9ca3af","#f5f5f5")
                                        row += f"<td style='padding:7px 10px;text-align:center;background:white'><span style='display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:50%;background:{bg2};color:{tc2};font-weight:700;font-size:11px'>{g}</span></td>"
                                    rows_html += f"<tr style='border-bottom:1px solid #f0f0f0'>{row}</tr>"
    
                                headers = "<th style='padding:7px 10px;text-align:left;font-size:12px;font-weight:600;color:#6b7280'>Yếu tố</th>"
                                headers += f"<th style='padding:7px 10px;text-align:center;font-size:12px;font-weight:600;color:#F26522'>{item['title'][:20]}</th>"
                                for h in other_items[:4]:
                                    headers += f"<th style='padding:7px 10px;text-align:center;font-size:12px;font-weight:600;color:#6b7280'>{h['title'][:20]}</th>"
    
                                st.markdown(f"""<div style="overflow-x:auto;background:white;border-radius:10px;border:1px solid #e8e8e8;margin-top:0.5rem">
                                  <table style="width:100%;border-collapse:collapse;background:white">
                                    <thead><tr style="background:#f9f9f9">{headers}</tr></thead>
                                    <tbody>{rows_html}</tbody>
                                  </table></div>""", unsafe_allow_html=True)
    
                                st.markdown("<br>", unsafe_allow_html=True)
                                st.markdown("Bấm **Phân tích so sánh với AI** để nhận phân tích chi tiết và giải thích tương đồng.")
    
    # ════════════════════════════════════════════════════════════════════════════════
    # TAB 3: TRA CỨU S-GRADE
    # ════════════════════════════════════════════════════════════════════════════════
    with tab3:
        if not JE_DATABASE:
            st.info("📭 Chưa có dữ liệu. Liên hệ admin để cập nhật file je_data.json.")
        else:
            # Filter: tên vị trí (dropdown) + S-Grade
            all_sgrades = sorted(set(d["s_grade"] for d in JE_DATABASE if d["s_grade"]))
    
            fc1, fc2 = st.columns([3, 1.5])
            with fc1:
                # 336 records — dùng tên + số thứ tự để phân biệt trùng tên
                all_labels = [
                    f"{d['title']}  |  {d['s_grade']}  |  {d['total_score']} điểm"
                    for d in JE_DATABASE
                ]
                selected_label = st.selectbox("Chọn vị trí", ["-- Chọn vị trí --"] + all_labels)
            with fc2:
                sg_filter = st.selectbox("Lọc S-Grade", ["Tất cả"] + all_sgrades)
    
            # Chỉ hiển thị khi đã chọn
            user_has_filtered = selected_label != "-- Chọn vị trí --" or sg_filter != "Tất cả"
    
            if not user_has_filtered:
                st.markdown("""<div style="background:#f9f9f9;border-radius:12px;padding:2.5rem;text-align:center;
                  color:#9ca3af;border:1px dashed #e8e8e8;margin-top:1rem">
                  <div style="font-size:28px;margin-bottom:0.5rem">🔍</div>
                  <div style="font-size:14px">Chọn vị trí hoặc S-Grade để bắt đầu tra cứu</div>
                </div>""", unsafe_allow_html=True)
            else:
                # Nếu chọn theo S-Grade thì lọc list
                if sg_filter != "Tất cả" and selected_label == "-- Chọn vị trí --":
                    filtered = [d for d in JE_DATABASE if d["s_grade"] == sg_filter]
                    st.markdown(f"<div style='font-size:13px;color:#9ca3af;margin:0.5rem 0 1rem'>Tìm thấy <strong>{len(filtered)}</strong> vị trí S-Grade {sg_filter}</div>", unsafe_allow_html=True)
                    sub_labels = [f"{d['title']}  |  {d['s_grade']}  |  {d['total_score']} điểm" for d in filtered]
                    selected_label = st.selectbox("Chọn vị trí cụ thể", sub_labels, label_visibility="collapsed")
                    sel_item = filtered[sub_labels.index(selected_label)]
                else:
                    idx = all_labels.index(selected_label) if selected_label in all_labels else 0
                    sel_item = JE_DATABASE[idx]
    
                    if sel_item:
                        # Badges: S-Grade + Tổng điểm
                        st.markdown(f"""<div style="display:flex;gap:10px;margin:1rem 0 0.5rem;flex-wrap:wrap">
                          <div style="background:#fff4ee;border-radius:8px;padding:8px 18px;border:1px solid #fcd4b8">
                            <span style="color:#9ca3af;font-size:12px">S-Grade</span><br>
                            <strong style="color:#F26522;font-size:20px">{sel_item['s_grade']}</strong>
                          </div>
                          <div style="background:#f3f4f6;border-radius:8px;padding:8px 18px;border:1px solid #e5e7eb">
                            <span style="color:#9ca3af;font-size:12px">Tổng điểm</span><br>
                            <strong style="color:#1f2937;font-size:20px">{sel_item['total_score']}</strong>
                          </div>
                        </div>""", unsafe_allow_html=True)
    
                        render_result_table(sel_item.get("factors", []), sel_item["title"], show_adjust=False)
    

# ── PAGE: TRA CỨU S-GRADE ───────────────────────────────────────────────────────
elif main_page == "lookup":
    st.markdown("""
    <div class="hero-banner" style="margin-bottom:1.5rem">
      <div class="hero-sub">Danh sách vị trí</div>
      <div class="hero-title" style="font-size:48px">TRA CỨU<br>S-GRADE</div>
      <div class="hero-tagline">491 vị trí — GHN Express, Logistics, Gido, SCOMMERCE</div>
    </div>
    """, unsafe_allow_html=True)

    if not POSITIONS:
        st.warning("Chưa có dữ liệu. Liên hệ admin để cập nhật file sgrade_positions.json.")
    else:
        # Filter state
        if "filter_open" not in st.session_state:
            st.session_state.filter_open = False
        if "f_search" not in st.session_state:
            st.session_state.f_search = ""
        if "f_rank" not in st.session_state:
            st.session_state.f_rank = "Tất cả"
        if "f_company" not in st.session_state:
            st.session_state.f_company = "Tất cả"
        if "f_block" not in st.session_state:
            st.session_state.f_block = "Tất cả"
        if "f_dept" not in st.session_state:
            st.session_state.f_dept = "Tất cả"

        # Filter bar
        fcol1, fcol2 = st.columns([6, 1])
        with fcol1:
            active_filters = sum([
                st.session_state.f_rank != "Tất cả",
                st.session_state.f_company != "Tất cả",
                st.session_state.f_block != "Tất cả",
                st.session_state.f_dept != "Tất cả",
                bool(st.session_state.f_search),
            ])
            badge = f" ({active_filters})" if active_filters else ""
            st.markdown(f"<div style='font-size:13px;color:#9ca3af;padding-top:8px'>{len(POSITIONS)} vị trí trong hệ thống</div>", unsafe_allow_html=True)
        with fcol2:
            if st.button(f"🔽 Bộ lọc{badge}", use_container_width=True):
                st.session_state.filter_open = not st.session_state.filter_open

        # Filter panel
        if st.session_state.filter_open:
            st.markdown("<div style='background:white;border:1px solid #e8e8e8;border-radius:12px;padding:1.25rem 1.5rem;margin-bottom:1rem'>", unsafe_allow_html=True)
            st.markdown("**Lọc hiển thị**")
            st.session_state.f_search = st.text_input("Tìm mã/tên vị trí", value=st.session_state.f_search, placeholder="Nhập mã/tên vị trí...")

            p1, p2 = st.columns(2)
            ranks_list = ["Tất cả"] + sorted(set(d["rank"] for d in POSITIONS if d["rank"]))
            companies_list = ["Tất cả"] + sorted(set(d["company"] for d in POSITIONS if d["company"]))
            blocks_list = ["Tất cả"] + sorted(set(d["block"] for d in POSITIONS if d["block"]))
            depts_list = ["Tất cả"] + sorted(set(d["department"] for d in POSITIONS if d["department"]))

            with p1:
                st.session_state.f_rank = st.selectbox("Cấp bậc", ranks_list, index=ranks_list.index(st.session_state.f_rank) if st.session_state.f_rank in ranks_list else 0)
                st.session_state.f_block = st.selectbox("Khối", blocks_list, index=blocks_list.index(st.session_state.f_block) if st.session_state.f_block in blocks_list else 0)
            with p2:
                st.session_state.f_company = st.selectbox("Công ty", companies_list, index=companies_list.index(st.session_state.f_company) if st.session_state.f_company in companies_list else 0)
                st.session_state.f_dept = st.selectbox("Phòng ban", depts_list, index=depts_list.index(st.session_state.f_dept) if st.session_state.f_dept in depts_list else 0)

            bc1, bc2 = st.columns([1,1])
            with bc1:
                if st.button("Xóa bộ lọc", use_container_width=True):
                    st.session_state.f_search = ""
                    st.session_state.f_rank = "Tất cả"
                    st.session_state.f_company = "Tất cả"
                    st.session_state.f_block = "Tất cả"
                    st.session_state.f_dept = "Tất cả"
                    st.rerun()
            with bc2:
                if st.button("Áp dụng", use_container_width=True):
                    st.session_state.filter_open = False
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        # Apply filters
        filtered = POSITIONS
        if st.session_state.f_search:
            q2 = st.session_state.f_search.lower()
            filtered = [d for d in filtered if q2 in d["positionName"].lower() or q2 in d["vietnameseName"].lower()]
        if st.session_state.f_rank != "Tất cả":
            filtered = [d for d in filtered if d["rank"] == st.session_state.f_rank]
        if st.session_state.f_company != "Tất cả":
            filtered = [d for d in filtered if d["company"] == st.session_state.f_company]
        if st.session_state.f_block != "Tất cả":
            filtered = [d for d in filtered if d["block"] == st.session_state.f_block]
        if st.session_state.f_dept != "Tất cả":
            filtered = [d for d in filtered if d["department"] == st.session_state.f_dept]

        st.markdown(f"<div style='font-size:13px;color:#9ca3af;margin:0.5rem 0 0.75rem'>Hiển thị <strong>{len(filtered)}</strong> / {len(POSITIONS)} vị trí</div>", unsafe_allow_html=True)

        # Table
        if filtered:
            rows_html = ""
            for d in filtered:
                rank = d.get("rank","")
                tc, bg = grade_color(rank)
                ptype = d.get("positionType","")
                type_color = "#185fa5" if ptype == "Indirect" else "#1a7a4a"
                type_bg = "#e6f1fb" if ptype == "Indirect" else "#f0faf5"
                rows_html += f"""<tr style="border-bottom:1px solid #f0f0f0;background:white">
                  <td style="padding:10px 14px;font-weight:500;font-size:13px;color:#1f2937">{d.get("positionName","")}</td>
                  <td style="padding:10px 14px;font-size:13px;color:#6b7280">{d.get("vietnameseName","")}</td>
                  <td style="padding:10px 14px;text-align:center">
                    <span style="display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;border-radius:50%;background:{bg};color:{tc};font-weight:700;font-size:12px">{rank}</span>
                  </td>
                  <td style="padding:10px 14px;font-size:13px;color:#6b7280">{d.get("block","")}</td>
                  <td style="padding:10px 14px;font-size:13px;color:#6b7280">{d.get("department","")}</td>
                  <td style="padding:10px 14px;text-align:center">
                    <span style="font-size:11px;font-weight:600;padding:3px 8px;border-radius:4px;background:{type_bg};color:{type_color}">{ptype}</span>
                  </td>
                </tr>"""

            st.markdown(f"""<div style="overflow-x:auto;background:white;border-radius:12px;border:1px solid #e8e8e8">
              <table style="width:100%;border-collapse:collapse;background:white">
                <thead><tr style="background:#F26522">
                  <th style="padding:12px 14px;text-align:left;font-size:13px;font-weight:700;color:white">Tên vị trí</th>
                  <th style="padding:12px 14px;text-align:left;font-size:13px;font-weight:700;color:white">Tên tiếng Việt</th>
                  <th style="padding:12px 14px;text-align:center;font-size:13px;font-weight:700;color:white">Cấp bậc</th>
                  <th style="padding:12px 14px;text-align:left;font-size:13px;font-weight:700;color:white">Khối</th>
                  <th style="padding:12px 14px;text-align:left;font-size:13px;font-weight:700;color:white">Phòng ban</th>
                  <th style="padding:12px 14px;text-align:center;font-size:13px;font-weight:700;color:white">Loại vị trí</th>
                </tr></thead>
                <tbody>{rows_html}</tbody>
              </table></div>""", unsafe_allow_html=True)

# ── PAGE: PHÚC LỢI THEO S-GRADE ─────────────────────────────────────────────────
elif main_page == "benefits":
    st.markdown("""
    <div class="hero-banner" style="margin-bottom:1.5rem">
      <div class="hero-sub">Chính sách đãi ngộ</div>
      <div class="hero-title" style="font-size:48px">PHÚC LỢI<br>THEO S-GRADE</div>
      <div class="hero-tagline">Grab for Work · Bảo hiểm sức khỏe · Khám sức khỏe</div>
    </div>
    """, unsafe_allow_html=True)

    ben1, ben2, ben3 = st.tabs(["🚗  Grab for Work", "🏥  Bảo hiểm sức khỏe", "🩺  Khám sức khỏe"])

    PROG_COLORS = {
        "Chương trình 5": ("#5b21b6", "#ede9fe"),
        "Chương trình 4": ("#185fa5", "#e6f1fb"),
        "Chương trình 3": ("#1a7a4a", "#f0faf5"),
        "Chương trình 2": ("#854f0b", "#faeeda"),
        "Chương trình 1": ("#6b7280", "#f3f4f6"),
    }
    def prog_badge(p):
        tc, bg = PROG_COLORS.get(p, ("#6b7280","#f3f4f6"))
        return '<span style="font-size:12px;font-weight:600;padding:4px 12px;border-radius:999px;background:' + bg + ';color:' + tc + '">' + p + '</span>'

    # TAB 1: GRAB FOR WORK
    with ben1:
        st.markdown("<br>", unsafe_allow_html=True)
        grab_data = [
            ("S13","Không giới hạn","Không giới hạn","Không giới hạn"),
            ("S12","Không giới hạn","Không giới hạn","Không giới hạn"),
            ("S11","Không giới hạn","Không giới hạn","Không giới hạn"),
            ("S10","Không giới hạn","Không giới hạn","Không giới hạn"),
            ("S9","5.000.000 đ","3.000.000 đ","3.000.000 đ"),
            ("S8","5.000.000 đ","3.000.000 đ","3.000.000 đ"),
            ("S7","3.000.000 đ","2.000.000 đ","2.000.000 đ"),
            ("S6","1.000.000 đ","1.000.000 đ","1.000.000 đ"),
            ("S5","1.000.000 đ","1.000.000 đ","1.000.000 đ"),
            ("S4","1.000.000 đ","1.000.000 đ","—"),
            ("S3","500.000 đ","500.000 đ","—"),
        ]
        def grab_cell(v):
            if v == "Không giới hạn":
                return '<td style="padding:10px 14px;text-align:center;border-bottom:1px solid #f0f0f0;color:#1a7a4a;font-weight:600;font-size:13px">∞ Không giới hạn</td>'
            elif v == "—":
                return '<td style="padding:10px 14px;text-align:center;border-bottom:1px solid #f0f0f0;color:#9ca3af;font-size:13px">—</td>'
            return '<td style="padding:10px 14px;text-align:center;border-bottom:1px solid #f0f0f0;color:#1f2937;font-weight:500;font-size:13px">' + v + '</td>'

        g_rows = ""
        for rank, kh, spkt, other in grab_data:
            tc, bg = grade_color(rank)
            g_rows += '<tr><td style="padding:10px 14px;text-align:center;border-bottom:1px solid #f0f0f0"><span style="display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;border-radius:50%;background:' + bg + ';color:' + tc + ';font-weight:700;font-size:12px">' + rank + '</span></td>' + grab_cell(kh) + grab_cell(spkt) + grab_cell(other) + '</tr>'

        st.markdown('<div style="background:white;border-radius:12px;border:1px solid #e8e8e8;overflow:hidden"><div style="background:#1f2937;padding:1rem 1.5rem"><span style="color:white;font-weight:600;font-size:15px">🚗 Chính sách Grab for Work — Hạn mức theo cấp bậc và khối</span></div><div style="padding:0.75rem 1.5rem;font-size:13px;color:#6b7280">Dựa theo từng cấp bậc của từng Khối sẽ được xác định mức chính sách cụ thể</div><table style="width:100%;border-collapse:collapse;background:white"><thead><tr style="background:#f3f4f6"><th style="padding:10px 14px;text-align:center;font-size:13px;font-weight:600;color:#374151;border-bottom:2px solid #e5e7eb">Cấp bậc</th><th style="padding:10px 14px;text-align:center;font-size:13px;font-weight:600;color:#374151;border-bottom:2px solid #e5e7eb">Khối Khách Hàng (trực tiếp)</th><th style="padding:10px 14px;text-align:center;font-size:13px;font-weight:600;color:#374151;border-bottom:2px solid #e5e7eb">Khối Sản Phẩm & Công Nghệ</th><th style="padding:10px 14px;text-align:center;font-size:13px;font-weight:600;color:#374151;border-bottom:2px solid #e5e7eb">Các Khối Còn Lại</th></tr></thead><tbody>' + g_rows + '</tbody></table></div>', unsafe_allow_html=True)

    # TAB 2: BẢO HIỂM SỨC KHỎE
    with ben2:
        st.markdown("<br>", unsafe_allow_html=True)
        ghn_ins = [
            ("S13","Chương trình 5","5"),("S12","Chương trình 5","5"),
            ("S11","Chương trình 5","4"),("S10","Chương trình 4","3"),
            ("S09","Chương trình 4","3"),("S08","Chương trình 4","2"),
            ("S07","Chương trình 4","2"),("S06","Chương trình 3","1"),
            ("S05","Chương trình 3","1"),("S04","Chương trình 2","0"),
            ("S03","Chương trình 2","0"),("S02","Chương trình 1","0"),
            ("S01","Chương trình 1","0"),
        ]
        rows1 = ""
        for rank, prog, rel in ghn_ins:
            tc, bg = grade_color(rank)
            rel_html = '<span style="color:#1a7a4a;font-weight:600">👥 ' + rel + ' người</span>' if rel != "0" else '<span style="color:#9ca3af">—</span>'
            rows1 += '<tr style="border-bottom:1px solid #f0f0f0;background:white"><td style="padding:9px 16px;text-align:center"><span style="display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;border-radius:50%;background:' + bg + ';color:' + tc + ';font-weight:700;font-size:12px">' + rank + '</span></td><td style="padding:9px 16px;text-align:center">' + prog_badge(prog) + '</td><td style="padding:9px 16px;text-align:center;font-size:13px">' + rel_html + '</td></tr>'

        aha_ins = [
            ("S12","G09","Chương trình 5","3"),("S09","G08","Chương trình 5","3"),
            ("S08","G07","Chương trình 4","3"),("S07","G06","Chương trình 4","2"),
            ("S06","G05","Chương trình 4","1"),("S04","G04","Chương trình 3","0"),
            ("S03","G03","Chương trình 3","0"),("S02","G02","Chương trình 2","0"),
            ("S01","G01","Chương trình 2","0"),
        ]
        rows2 = ""
        for rank, ggrade, prog, rel in aha_ins:
            tc, bg = grade_color(rank)
            rel_html = '<span style="color:#1a7a4a;font-weight:600">👥 ' + rel + ' người</span>' if rel != "0" else '<span style="color:#9ca3af">—</span>'
            rows2 += '<tr style="border-bottom:1px solid #f0f0f0;background:white"><td style="padding:9px 16px;text-align:center"><span style="display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;border-radius:50%;background:' + bg + ';color:' + tc + ';font-weight:700;font-size:12px">' + rank + '</span></td><td style="padding:9px 16px;text-align:center;font-size:13px;color:#6b7280;font-weight:500">' + ggrade + '</td><td style="padding:9px 16px;text-align:center">' + prog_badge(prog) + '</td><td style="padding:9px 16px;text-align:center;font-size:13px">' + rel_html + '</td></tr>'

        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div style="background:white;border-radius:12px;border:1px solid #e8e8e8;overflow:hidden"><div style="background:#1f2937;padding:0.875rem 1.25rem"><span style="color:white;font-weight:600;font-size:14px">🏢 SCommerce / GHN / Nặng / Logistics</span></div><table style="width:100%;border-collapse:collapse;background:white"><thead><tr style="background:#f3f4f6"><th style="padding:9px 16px;text-align:center;font-size:12px;font-weight:600;color:#374151;border-bottom:1.5px solid #e5e7eb">S-Grade</th><th style="padding:9px 16px;text-align:center;font-size:12px;font-weight:600;color:#374151;border-bottom:1.5px solid #e5e7eb">Chương trình</th><th style="padding:9px 16px;text-align:center;font-size:12px;font-weight:600;color:#374151;border-bottom:1.5px solid #e5e7eb">Người thân CT chi trả</th></tr></thead><tbody>' + rows1 + '</tbody></table></div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div style="background:white;border-radius:12px;border:1px solid #e8e8e8;overflow:hidden"><div style="background:#1f2937;padding:0.875rem 1.25rem"><span style="color:white;font-weight:600;font-size:14px">🛵 Ahamove</span></div><table style="width:100%;border-collapse:collapse;background:white"><thead><tr style="background:#f3f4f6"><th style="padding:9px 16px;text-align:center;font-size:12px;font-weight:600;color:#374151;border-bottom:1.5px solid #e5e7eb">S-Grade</th><th style="padding:9px 16px;text-align:center;font-size:12px;font-weight:600;color:#374151;border-bottom:1.5px solid #e5e7eb">G-Grade</th><th style="padding:9px 16px;text-align:center;font-size:12px;font-weight:600;color:#374151;border-bottom:1.5px solid #e5e7eb">Chương trình</th><th style="padding:9px 16px;text-align:center;font-size:12px;font-weight:600;color:#374151;border-bottom:1.5px solid #e5e7eb">Người thân</th></tr></thead><tbody>' + rows2 + '</tbody></table></div>', unsafe_allow_html=True)

    # TAB 3: KHÁM SỨC KHỎE
    with ben3:
        st.markdown("<br>", unsafe_allow_html=True)
        health_data = [
            ("Chương trình 5", "SMT — 4 người thân đi kèm", "S11 – S13", "G9", "4 người"),
            ("Chương trình 4", "S.Director + 3 người thân<br>Director + 1 người thân<br>Senior Manager / Tech Leaders<br>Senior Lead Engineer 1&amp;2 / Lead Engineer 1&amp;2", "S7 – S10", "G6 – G8", "S10: 3 người<br>S9/G8: 2 người<br>S8/G7: 1 người<br>S7: 0 người"),
            ("Chương trình 3", "Mid manager", "S5 – S6", "G3 – G5", "0"),
            ("Chương trình 2", "Nhóm Văn phòng: Level Executive trở lên<br>Nhóm Kho (KTC+KHL+FFM): NV ký HĐLĐ &amp; CTV ≥3 tháng<br>Giao Hàng Nặng: NV ký HĐLĐ &amp; CTV ≥3 tháng", "S1 – S4", "G1 – G2", "0"),
            ("Chương trình 1", "Tài xế xe tải ký HĐLĐ với GHN, thâm niên >3 tháng tính đến 30/04/2026", "Tài xế xe tải", "—", "0"),
        ]
        rows3 = ""
        for prog, target, ghn, aha, rel in health_data:
            rel_color = "#1a7a4a" if rel != "0" else "#9ca3af"
            rows3 += '<tr style="border-bottom:1px solid #f0f0f0;background:white;vertical-align:top"><td style="padding:12px 14px">' + prog_badge(prog) + '</td><td style="padding:12px 14px;font-size:12px;color:#6b7280;line-height:1.7">' + target + '</td><td style="padding:12px 14px;text-align:center;font-size:13px;font-weight:600;color:#F26522">' + ghn + '</td><td style="padding:12px 14px;text-align:center;font-size:13px;font-weight:600;color:#185fa5">' + aha + '</td><td style="padding:12px 14px;text-align:center;font-size:12px;color:' + rel_color + ';line-height:1.6">' + rel + '</td></tr>'

        st.markdown('<div style="background:white;border-radius:12px;border:1px solid #e8e8e8;overflow:hidden"><div style="background:#1f2937;padding:1rem 1.5rem"><span style="color:white;font-weight:600;font-size:15px">🩺 Chương trình Khám sức khỏe 2026</span></div><table style="width:100%;border-collapse:collapse;background:white"><thead><tr style="background:#f3f4f6"><th style="padding:10px 14px;text-align:left;font-size:13px;font-weight:600;color:#374151;border-bottom:2px solid #e5e7eb">Chương trình</th><th style="padding:10px 14px;text-align:left;font-size:13px;font-weight:600;color:#374151;border-bottom:2px solid #e5e7eb">Đối tượng</th><th style="padding:10px 14px;text-align:center;font-size:13px;font-weight:600;color:#374151;border-bottom:2px solid #e5e7eb">Nhân viên GHN</th><th style="padding:10px 14px;text-align:center;font-size:13px;font-weight:600;color:#374151;border-bottom:2px solid #e5e7eb">Nhân viên Ahamove</th><th style="padding:10px 14px;text-align:center;font-size:13px;font-weight:600;color:#374151;border-bottom:2px solid #e5e7eb">Người thân</th></tr></thead><tbody>' + rows3 + '</tbody></table></div>', unsafe_allow_html=True)
